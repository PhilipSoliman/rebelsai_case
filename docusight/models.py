from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


# User table for Dropbox integration
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    display_name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    dropbox_account_id = Column(String, unique=True, nullable=False)
    dropbox_access_token = Column(String, nullable=False)
    dropbox_refresh_token = Column(String, nullable=False)
    dropbox_access_token_expiration = Column(DateTime, nullable=True)

    # Relationships
    folders = relationship("Folder", back_populates="user")
    documents = relationship("Document", back_populates="user")
    classifications = relationship("Classification", back_populates="user")

    def __repr__(self):  # NOTE: used for logging purposes
        return f"User(id={self.id}, email={self.email}, dropbox_account_id={self.dropbox_account_id})"


class Folder(Base):
    __tablename__ = "folders"

    id = Column(Integer, primary_key=True, index=True)
    path = Column(String, unique=True, index=True)
    name = Column(String, index=True)
    parent_id = Column(Integer, ForeignKey("folders.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Relationship to Documents, User, and other Folders
    documents = relationship("Document", back_populates="folder")
    subfolders = relationship("Folder", back_populates="parent_folder")
    parent_folder = relationship(
        "Folder", back_populates="subfolders", remote_side=[id]
    )
    user = relationship("User", back_populates="folders")


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    folder_id = Column(Integer, ForeignKey("folders.id"))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # original file meta
    filename = Column(String, index=True)
    path = Column(String)
    size = Column(Integer)
    created = Column(Float)
    modified = Column(Float)

    # dropbox meta
    dropbox_path = Column(String, nullable=True)
    plain_text_size = Column(Integer, nullable=True)

    # Relationships to Folder, User, and Classification
    folder = relationship("Folder", back_populates="documents")
    user = relationship("User", back_populates="documents")
    classification = relationship("Classification", back_populates="document")


class Classification(Base):
    __tablename__ = "classifications"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    label = Column(String)
    score = Column(String)

    # Relationships to Document and User
    document = relationship("Document", back_populates="classification")
    user = relationship("User", back_populates="classifications")
