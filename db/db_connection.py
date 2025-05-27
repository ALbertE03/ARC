import os
from neo4j import GraphDatabase
import pandas as pd
from dotenv import load_dotenv


load_dotenv()


class Neo4jConnection:
    def __init__(self):
        """Initialize the Neo4j connection using environment variables"""
        self.uri = os.getenv("URL")
        self.user = os.getenv("USER_NEO")
        self.password = os.getenv("PASS_NEO")

        if not all([self.uri, self.user, self.password]):
            raise ValueError(
                "Missing Neo4j credentials. Make sure URL, USER_NEO and PASS_NEO are set in your .env file"
            )

        self.driver = None

    def connect(self):
        """Establish connection to Neo4j database"""
        if not self.driver:
            self.driver = GraphDatabase.driver(
                self.uri, auth=(self.user, self.password)
            )
        return self.driver

    def close(self):
        """Close the Neo4j connection"""
        if self.driver:
            self.driver.close()
            self.driver = None

    def execute_query(self, query, params=None, return_data=True):
        """
        Execute a Cypher query against the Neo4j database with enhanced error handling

        Args:
            query (str): The Cypher query to execute
            params (dict): Parameters for the query
            return_data (bool): Whether to return the results or not

        Returns:
            list or None: Query results if return_data is True, None otherwise
        """
        if not query or not isinstance(query, str):
            raise ValueError("Query must be a non-empty string")
            
        if not self.driver:
            self.connect()

        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                with self.driver.session() as session:
                    if return_data:
                        result = session.run(query, params or {})
                        return [record.data() for record in result]
                    else:
                        session.run(query, params or {})
                        return None
                        
            except Exception as e:
                retry_count += 1
                error_msg = f"Error executing query (attempt {retry_count}/{max_retries}): {e}"
                
                if retry_count < max_retries:
                    print(f"{error_msg} - Retrying...")
                    # Reconnect before retrying
                    try:
                        self.close()
                        self.connect()
                    except:
                        pass
                else:
                    print(f"{error_msg} - Max retries reached")
                    raise e

    def query_to_dataframe(self, query, params=None):
        """
        Execute a query and return the results as a pandas DataFrame

        Args:
            query (str): The Cypher query to execute
            params (dict): Parameters for the query

        Returns:
            DataFrame: The query results as a pandas DataFrame
        """
        results = self.execute_query(query, params)
        if not results:
            return pd.DataFrame()

        flattened = []
        for row in results:
            flat_row = {}
            for k, v in row.items():
                if isinstance(v, dict) and "properties" in v:
                    for prop_key, prop_val in v["properties"].items():
                        flat_row[f"{k}_{prop_key}"] = prop_val
                else:
                    flat_row[k] = v
            flattened.append(flat_row)

        return pd.DataFrame(flattened)
