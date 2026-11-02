from app.database.database import Base, engine
# Import models to ensure they are registered on Base.metadata
import app.models  # noqa: F401


def init_db():
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully.")


if __name__ == "__main__":
    init_db()
