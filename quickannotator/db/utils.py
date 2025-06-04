from sqlalchemy.orm import Query
from quickannotator.db import db_session, engine
from sqlalchemy import Table


def get_query_as_sql(query: Query) -> str:
    """
    Returns the SQL query as a string.

    dialect allows us to avoid code splitting depending on the dialect. If not used, compile() will not use sqlite dialect functions including ScaleCoords
    """
    return query.statement.compile(compile_kwargs={"literal_binds": True}, dialect=db_session.bind.dialect).string

