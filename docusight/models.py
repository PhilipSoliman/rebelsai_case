from sqlalchemy import Column, Float, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Folder(Base):
    __tablename__ = "folders"

    id = Column(Integer, primary_key=True, index=True)
    path = Column(String, unique=True, index=True)
    name = Column(String, index=True)
    parent_id = Column(Integer, ForeignKey("folders.id"), nullable=True)

    # Relationship to Documents and other Folders
    documents = relationship("Document", back_populates="folder")
    subfolders = relationship("Folder", back_populates="parent_folder")
    parent_folder = relationship(
        "Folder", back_populates="subfolders", remote_side=[id]
    )


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    folder_id = Column(Integer, ForeignKey("folders.id"))

    # original file meta
    filename = Column(String, index=True)
    path = Column(String)
    size = Column(Integer)
    created = Column(Float)
    modified = Column(Float)

    # dropbox meta
    dropbox_path = Column(String, nullable=True)
    plain_text_size = Column(Integer, nullable=True)

    # Relationships to Folder and Classification
    folder = relationship("Folder", back_populates="documents")
    classifications = relationship("Classification", back_populates="document")


class Classification(Base):
    __tablename__ = "classifications"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"))
    label = Column(String)
    score = Column(String)

    # Relationship to Document
    document = relationship("Document", back_populates="classifications")
