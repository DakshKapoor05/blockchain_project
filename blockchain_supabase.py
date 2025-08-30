import streamlit as st
import pandas as pd
import json
import hashlib
from datetime import datetime
from supabase import create_client, Client


class BlockchainSupabaseDB:
    def __init__(self):
        # Initialize Supabase client
        url = st.secrets["supabase_url"]
        key = st.secrets["supabase_key"]
        self.supabase: Client = create_client(url, key)
        self.chain = []
        self.load_existing_chain()
        if len(self.chain) == 0:
            self.create_genesis_block()

    def add_student_grade(self, student_name, student_id, subject, grade, semester, remarks=""):
        """Add student grade to Supabase"""
        try:
            # Insert into student_grades table
            result = self.supabase.table("student_grades").insert({
                "student_name": student_name,
                "student_id": student_id,
                "subject": subject,
                "grade": grade,
                "semester": semester,
                "remarks": remarks
            }).execute()

            if result.data:
                record_id = result.data[0]['id']

                # Create blockchain record
                timestamp = datetime.now().isoformat()
                record_data = {
                    'sql_id': record_id,
                    'student_name': student_name,
                    'student_id': student_id,
                    'subject': subject,
                    'grade': grade,
                    'semester': semester,
                    'remarks': remarks,
                    'timestamp': timestamp,
                    'operation': 'INSERT'
                }

                # Calculate blockchain hash
                previous_block = self.chain[-1] if self.chain else {'hash': '0'}
                new_index = len(self.chain)
                new_hash = self.calculate_hash(new_index, timestamp, record_data, previous_block['hash'])

                # Create new block
                new_block = {
                    'index': new_index,
                    'timestamp': timestamp,
                    'data': record_data,
                    'previous_hash': previous_block['hash'],
                    'hash': new_hash,
                    'sql_operation': f'INSERT ID:{record_id}'
                }

                # Store blockchain record
                self.supabase.table("blockchain_log").insert({
                    "block_index": new_block['index'],
                    "timestamp": new_block['timestamp'],
                    "data_hash": json.dumps(record_data, sort_keys=True),
                    "previous_hash": new_block['previous_hash'],
                    "block_hash": new_block['hash'],
                    "sql_operation": new_block['sql_operation']
                }).execute()

                self.chain.append(new_block)
                return new_block, record_id

        except Exception as e:
            return None, f"Database error: {str(e)}"

    def get_all_grades_sql(self):
        """Get all grades from Supabase"""
        try:
            result = self.supabase.table("student_grades").select("*").eq("is_verified", True).execute()
            df = pd.DataFrame(result.data if result.data else [])
            return df
        except:
            return pd.DataFrame()

    def get_student_grades_by_id(self, student_id):
        """Get grades for specific student"""
        try:
            result = self.supabase.table("student_grades").select("*").eq("student_id", student_id).eq("is_verified",
                                                                                                       True).execute()
            df = pd.DataFrame(result.data if result.data else [])
            return df
        except:
            return pd.DataFrame()

    def search_students_sql(self, search_term):
        """Search students"""
        try:
            result = self.supabase.table("student_grades").select("*").eq("is_verified", True).execute()
            df = pd.DataFrame(result.data if result.data else [])
            if not df.empty:
                mask = (
                        df['student_name'].astype(str).str.contains(search_term, case=False, na=False) |
                        df['student_id'].astype(str).str.contains(search_term, case=False, na=False) |
                        df['subject'].astype(str).str.contains(search_term, case=False, na=False)
                )
                return df[mask]
            return df
        except:
            return pd.DataFrame()

    def delete_student_grade(self, record_id, reason="Deleted by user"):
        """Logically delete a student grade"""
        try:
            # Update record as deleted
            self.supabase.table("student_grades").update({
                "is_verified": False,
                "remarks": f"Deleted: {reason}"
            }).eq("id", record_id).execute()

            # Add blockchain deletion record
            timestamp = datetime.now().isoformat()
            delete_data = {
                'sql_id': record_id,
                'operation': 'DELETE',
                'reason': reason,
                'timestamp': timestamp
            }

            previous_block = self.chain[-1] if self.chain else {'hash': '0'}
            new_index = len(self.chain)
            new_hash = self.calculate_hash(new_index, timestamp, delete_data, previous_block['hash'])

            new_block = {
                'index': new_index,
                'timestamp': timestamp,
                'data': delete_data,
                'previous_hash': previous_block['hash'],
                'hash': new_hash,
                'sql_operation': f'DELETE ID:{record_id}'
            }

            self.supabase.table("blockchain_log").insert({
                "block_index": new_block['index'],
                "timestamp": new_block['timestamp'],
                "data_hash": json.dumps(delete_data, sort_keys=True),
                "previous_hash": new_block['previous_hash'],
                "block_hash": new_block['hash'],
                "sql_operation": new_block['sql_operation']
            }).execute()

            self.chain.append(new_block)
            return new_block, record_id

        except Exception as e:
            return None, f"Delete error: {str(e)}"

    def load_existing_chain(self):
        """Load blockchain from Supabase"""
        try:
            result = self.supabase.table("blockchain_log").select("*").order("block_index").execute()
            if result.data:
                for row in result.data:
                    try:
                        data = json.loads(row['data_hash'])
                    except:
                        data = row['data_hash']

                    block = {
                        'index': row['block_index'],
                        'timestamp': row['timestamp'],
                        'data': data,
                        'previous_hash': row['previous_hash'],
                        'hash': row['block_hash'],
                        'sql_operation': row['sql_operation']
                    }
                    self.chain.append(block)
        except:
            self.chain = []

    def calculate_hash(self, index, timestamp, data, previous_hash):
        """Calculate blockchain hash"""
        if isinstance(data, dict):
            data_str = json.dumps(data, sort_keys=True, separators=(',', ':'))
        else:
            data_str = str(data)

        hash_string = f"{index}|{timestamp}|{data_str}|{previous_hash}"
        return hashlib.sha256(hash_string.encode('utf-8')).hexdigest()

    def create_genesis_block(self):
        """Create genesis block"""
        timestamp = datetime.now().isoformat()
        genesis_block = {
            'index': 0,
            'timestamp': timestamp,
            'data': 'Genesis Block - Student Grade System',
            'previous_hash': '0',
            'hash': '',
            'sql_operation': 'INIT_DB'
        }

        genesis_block['hash'] = self.calculate_hash(0, timestamp, genesis_block['data'], '0')
        self.chain.append(genesis_block)

        # Store in Supabase
        try:
            self.supabase.table("blockchain_log").insert({
                "block_index": genesis_block['index'],
                "timestamp": genesis_block['timestamp'],
                "data_hash": str(genesis_block['data']),
                "previous_hash": genesis_block['previous_hash'],
                "block_hash": genesis_block['hash'],
                "sql_operation": genesis_block['sql_operation']
            }).execute()
        except:
            pass  # Genesis might already exist

    def verify_blockchain_integrity(self):
        """Verify blockchain integrity"""
        if len(self.chain) <= 1:
            return True, "Genesis block or empty blockchain is valid"

        for i in range(1, len(self.chain)):
            current_block = self.chain[i]
            previous_block = self.chain[i - 1]

            expected_hash = self.calculate_hash(
                current_block['index'],
                current_block['timestamp'],
                current_block['data'],
                current_block['previous_hash']
            )

            if current_block['hash'] != expected_hash:
                return False, f"Block {i} hash is invalid"

            if current_block['previous_hash'] != previous_block['hash']:
                return False, f"Block {i} chain link is broken"

        return True, "Blockchain is valid"

    def get_blockchain_stats(self):
        """Get blockchain statistics"""
        df = self.get_all_grades_sql()
        sql_count = len(df) if not df.empty else 0

        return {
            'sql_count': sql_count,
            'blockchain_count': len(self.chain) - 1 if self.chain else 0
        }

    def reset_database(self):
        """Reset the entire database"""
        try:
            # Delete all records (Supabase doesn't allow TRUNCATE)
            self.supabase.table("student_grades").delete().neq("id", 0).execute()
            self.supabase.table("blockchain_log").delete().neq("block_index", -1).execute()

            # Reinitialize
            self.chain = []
            self.create_genesis_block()

            return True, "Database reset successfully"

        except Exception as e:
            return False, f"Reset error: {str(e)}"

