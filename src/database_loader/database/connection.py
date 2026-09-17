from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError


class Database:

    def __init__(self, settings):

        self.engine = create_engine(
            f"postgresql+psycopg2://"
            f"{settings.db_user}:{settings.db_password}"
            f"@{settings.db_host}:{settings.db_port}/"
            f"{settings.db_name}",
            pool_pre_ping=True,
            future=True,
        )

    def test_connection(self):
        """
        Tests the connection to the PostgreSQL database.

        Raises:
            SQLAlchemyError: If the connection cannot be established or the
                validation query fails.
        """

        with self.engine.connect() as conn:
            conn.execute(text("SELECT 1"))

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
