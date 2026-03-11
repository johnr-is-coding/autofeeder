from app.domain.models.report import Report

def main()-> None:
    indexed_cols = set()
    for index in Report.__table__.indexes:
        for column in index.columns:
            indexed_cols.add(column.name)

    print(list(indexed_cols))
    column_names = [column.key for column in Report.__table__.columns]
    print(column_names)