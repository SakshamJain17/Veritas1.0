"""Persistent VERITAS entities. IDs and timestamps are supplied by the service layer."""
from sqlalchemy import Column, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import declarative_base

Base=declarative_base()

class User(Base):
    __tablename__="users"
    id=Column(String,primary_key=True);email=Column(String,unique=True);role=Column(String,nullable=False);created_at=Column(String,nullable=False)

class Document(Base):
    __tablename__="documents"
    id=Column(String,primary_key=True);name=Column(String);mime=Column(String);size=Column(Integer);sha256=Column(String);path=Column(Text);text=Column(Text);created_at=Column(String)

class OCRSpan(Base):
    __tablename__="ocr_spans"
    id=Column(String,primary_key=True);document_id=Column(String,ForeignKey("documents.id"));page=Column(Integer);text=Column(Text);bbox=Column(Text);confidence=Column(Float);created_at=Column(String)

class Claim(Base):
    __tablename__="claims"
    id=Column(String,primary_key=True);document_id=Column(String,ForeignKey("documents.id"));field=Column(String);original_value=Column(Text);normalized_value=Column(Text);confidence=Column(Float);page=Column(Integer);bbox=Column(Text);status=Column(String);created_at=Column(String)

class NormalizedClaimValue(Base):
    __tablename__="normalized_claim_values"
    id=Column(String,primary_key=True);claim_id=Column(String,ForeignKey("claims.id"));value=Column(Text);unit=Column(String);rule=Column(String);created_at=Column(String)

class SourceRegistryEntry(Base):
    __tablename__="source_registry"
    id=Column(String,primary_key=True);hostname=Column(String,unique=True);claim_types=Column(Text);authority=Column(String);created_at=Column(String)

class Investigation(Base):
    __tablename__="investigations"
    id=Column(String,primary_key=True);kind=Column(String);status=Column(String);request=Column(Text);result=Column(Text);error=Column(Text);started_at=Column(String);finished_at=Column(String)

class TinyFishExecutionRun(Base):
    __tablename__="tinyfish_runs"
    id=Column(String,primary_key=True);investigation_id=Column(String,ForeignKey("investigations.id"));capability=Column(String);external_run_id=Column(String);status=Column(String);trace=Column(Text);started_at=Column(String);finished_at=Column(String)

class Evidence(Base):
    __tablename__="evidence"
    id=Column(String,primary_key=True);claim_id=Column(String,ForeignKey("claims.id"));investigation_id=Column(String);url=Column(Text);method=Column(String);excerpt=Column(Text);content_sha256=Column(String);checks=Column(Text);created_at=Column(String)

class ClaimVerificationDecision(Base):
    __tablename__="verification_decisions"
    id=Column(String,primary_key=True);claim_id=Column(String,ForeignKey("claims.id"));status=Column(String);reason_code=Column(String);checks=Column(Text);created_at=Column(String)

class HumanReviewDecision(Base):
    __tablename__="reviews"
    id=Column(String,primary_key=True);claim_id=Column(String,ForeignKey("claims.id"));decision=Column(String);reason=Column(Text);corrected_value=Column(Text);created_at=Column(String)

class Attestation(Base):
    __tablename__="attestations"
    id=Column(String,primary_key=True);claim_id=Column(String,ForeignKey("claims.id"));status=Column(String);issuer=Column(String);payload=Column(Text);hash=Column(String);revoked=Column(Integer,default=0);created_at=Column(String)

class AuditEvent(Base):
    __tablename__="audit_events"
    id=Column(String,primary_key=True);event=Column(String);subject_id=Column(String);detail=Column(Text);created_at=Column(String)

class Comparison(Base):
    __tablename__="comparisons"
    id=Column(String,primary_key=True);claim_a=Column(Text);claim_b=Column(Text);result=Column(Text);created_at=Column(String)
