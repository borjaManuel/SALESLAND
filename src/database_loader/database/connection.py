from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError


class Database:

    def __init__(self, settings):

        self.schema = settings.db_schema

        connect_args = {}
        if self.schema:
            # Unqualified table names in every query resolve to this schema.
            connect_args["options"] = f"-c search_path={self.schema}"

        self.engine = create_engine(
            f"postgresql+psycopg2://"
            f"{settings.db_user}:{settings.db_password}"
            f"@{settings.db_host}:{settings.db_port}/"
            f"{settings.db_name}",
            pool_pre_ping=True,
            future=True,
            connect_args=connect_args,
        )

    def test_connection(self):
        """
        Tests the connection to the PostgreSQL database and, when a schema
        is configured, checks that it exists.

        Raises:
            SQLAlchemyError: If the connection cannot be established or the
                validation query fails.
            RuntimeError: If the configured schema does not exist.
        """

        with self.engine.connect() as conn:
            current_schema = conn.execute(text("SELECT current_schema()")).scalar()

        if self.schema and current_schema != self.schema:
            raise RuntimeError(
                f"Database schema '{self.schema}' does not exist or is not accessible"
            )

    def get_connection(self):
        """
        Creates and returns a new database connection.

        Returns:
            Connection: An active SQLAlchemy connection.
        """
        return self.engine.connect()

    def dispose(self):
        """
        Releases all connections in the SQLAlchemy connection pool.

        This method should be called when the application is shutting down
        to ensure that all database resources are properly released.
        """
        self.engine.dispose()
