from db import get_engine
from sqlalchemy import text

def percent_calculation(rack_id, activity_id, cable_id, position, quantity):

    engine = get_engine()

    with engine.connect() as conn:
        planned = conn.execute(text("""
            SELECT quantity FROM rack_results 
            WHERE rack_id = :rack_id AND activity_id = :activity_id 
                AND cable_type_id = :cable_type_id AND position = :position
            """), {
                "rack_id": rack_id,
                "activity_id": activity_id,
                "cable_type_id": cable_id,
                "position": position
            }).scalar()

        if planned and planned > 0:
            return round(quantity / planned * 100, 1)

        return 0