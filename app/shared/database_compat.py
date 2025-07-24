"""
Database compatibility layer to bridge SQLAlchemy and asyncpg
"""
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional
import re
import logging
from sqlalchemy import text
from .database import get_db_session as get_asyncpg_session

logger = logging.getLogger(__name__)


class AsyncpgSQLAlchemyAdapter:
    """Adapter to make asyncpg connections work with SQLAlchemy-style code"""
    
    def __init__(self, connection):
        self.connection = connection
    
    async def execute(self, query, params=None):
        """Execute a query with SQLAlchemy-style interface"""
        if hasattr(query, 'text'):
            # It's a SQLAlchemy text() object
            sql = str(query)
        else:
            # It's a raw SQL string
            sql = str(query)
            
        # Convert SQLAlchemy named parameters (:param) to PostgreSQL ($1, $2, etc)
        if params and ':' in sql:
            # Find all unique parameter names
            param_pattern = r':(\w+)'
            all_matches = re.findall(param_pattern, sql)
            unique_params = list(dict.fromkeys(all_matches))  # Preserve order, remove duplicates
            
            if unique_params:
                # Replace each unique parameter with its positional equivalent
                param_values = []
                new_sql = sql
                
                for i, param_name in enumerate(unique_params, 1):
                    if param_name in params:
                        param_values.append(params[param_name])
                        # Replace ALL occurrences of this parameter
                        new_sql = re.sub(f':{param_name}\\b', f'${i}', new_sql)
                    else:
                        logger.warning(f"Parameter '{param_name}' not found in params dict")
                        param_values.append(None)
                
                # Execute with positional parameters
                try:
                    result = await self.connection.fetch(new_sql, *param_values)
                except Exception as e:
                    logger.error(f"SQL execution failed. SQL: {new_sql}, Params: {param_values}, Error: {e}")
                    raise
            else:
                result = await self.connection.fetch(sql)
        elif params:
            # Params provided but no named parameters in SQL - assume positional
            if isinstance(params, dict):
                # If it's a dict with numeric keys, convert to list
                if all(isinstance(k, (int, str)) and str(k).isdigit() for k in params.keys()):
                    param_list = [params[str(k)] for k in sorted(int(k) for k in params.keys())]
                    result = await self.connection.fetch(sql, *param_list)
                else:
                    # Use values in order
                    result = await self.connection.fetch(sql, *params.values())
            else:
                result = await self.connection.fetch(sql, *params)
        else:
            # No parameters
            result = await self.connection.fetch(sql)
        
        # Return a result object that mimics SQLAlchemy's behavior
        return AsyncpgResult(result)
    
    async def scalar(self, query, params=None):
        """Execute a query and return a single scalar value"""
        result = await self.execute(query, params)
        rows = list(result)
        if rows and len(rows) > 0:
            row = rows[0]
            if hasattr(row, 'values'):
                values = list(row.values())
                return values[0] if values else None
            return row[0] if row else None
        return None


class AsyncpgResult:
    """Result wrapper to make asyncpg results work like SQLAlchemy results"""
    
    def __init__(self, records):
        self.records = records
    
    def __iter__(self):
        """Allow iteration over results"""
        for record in self.records:
            yield AsyncpgRow(record)
    
    def __len__(self):
        return len(self.records)
    
    def scalar(self):
        """Get first column of first row"""
        if self.records:
            return self.records[0][0]
        return None
    
    def scalars(self):
        """Get first column of all rows"""
        return [record[0] for record in self.records]


class AsyncpgRow:
    """Row wrapper to make asyncpg records work like SQLAlchemy rows"""
    
    def __init__(self, record):
        self.record = record
    
    def __getattr__(self, name):
        """Allow attribute-style access to columns"""
        try:
            return self.record[name]
        except KeyError:
            raise AttributeError(f"Row has no attribute '{name}'")
    
    def __getitem__(self, key):
        """Allow dict-style access to columns"""
        return self.record[key]
    
    def values(self):
        """Get all values as a list"""
        return list(self.record.values())
    
    def keys(self):
        """Get all column names"""
        return list(self.record.keys())


@asynccontextmanager
async def get_db_session():
    """Get a database session with SQLAlchemy-compatible interface"""
    async with get_asyncpg_session() as connection:
        yield AsyncpgSQLAlchemyAdapter(connection)


# Export the compatible session getter
__all__ = ['get_db_session']