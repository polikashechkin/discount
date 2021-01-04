#import json, datetime, random, arrow, re
from domino.core import log
import datetime
from sqlalchemy import Column, Index, String, BigInteger, DateTime, insert, Integer, insert
from sqlalchemy.dialects.postgresql import JSONB
from domino.databases.postgres import Postgres

#def on_activate(account_id, msglog):
#    table = Postgres.Table(ReportLineTable)
#    table.migrate(account_id, msglog)

class ReportLine(Postgres.Base):

    __tablename__ = 'report_line'

    id              = Column(BigInteger, primary_key=True, autoincrement = True, nullable =False)
    report_id       = Column(BigInteger, nullable=False)
    info            = Column(JSONB)
    Index('', report_id, id)

    def __repr__(self):
        return f'<ReportLine(report_id={self.report_id}, info={self.info})>'
        
    @staticmethod
    def insert(postgres, report_id, info):
        values = {
            ReportLineTable.c.report_id : report_id,
            ReportLineTable.c.info : info
        }
        postgres.execute(insert(ReportLineTable).values(values))

ReportLineTable = ReportLine.__table__
Postgres.Table(ReportLineTable)


