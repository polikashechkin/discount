#import json, datetime, arrow
from sqlalchemy import Column, Integer, String, JSON, DateTime, or_, and_
from sqlalchemy.dialects.oracle import RAW, NUMBER
from sqlalchemy.orm import aliased

from domino.core import log
from domino.databases.oracle import RawToHex, HexToRaw
from domino.tables.oracle.DB1_DOCUMENT import DB1_DOCUMENT

class InvoiceDocument(DB1_DOCUMENT):

    __tablename__ = 'db1_document'
    __table_args__ = {'extend_existing': True}
      
    #egais_document_id  = Column('f15073282', RAW(8))
    
    #@property
    #def egais_document_ID(self):
    #    return RawToHex(self.egais_document_id)

    #F15073282
    def __repr__(self):
        return f'<InvoiceDocument(id={self.ID}, type={self.TYPE})>'
 
InvoiceDocument.Class = (InvoiceDocument.CLASS == 65537)
InvoiceDocument.ClassType = and_(InvoiceDocument.CLASS == 14286850, InvoiceDocument.TYPE.in_([14286901]))
InvoiceDocumentTable = InvoiceDocument.__table__

_InvoiceDocument = aliased(InvoiceDocument)
#InvoiceDocumentTable = InvoiceDocument.__table__.alias('invoice_document')