
from app import app, db, Screen, Seat

with app.app_context():

    screens = Screen.query.filter(Screen.id >= 55).all()

    for screen in screens:

        # Skip if seats already exist
        if Seat.query.filter_by(screen_id=screen.id).count() > 0:
            continue

        for row in range(screen.total_rows):
            row_letter = chr(65 + row)

            for seat in range(1, screen.seats_per_row + 1):

                seat_number = f"{row_letter}{seat}"

                db.session.add(
                    Seat(
                        screen_id=screen.id,
                        seat_number=seat_number,
                        status="Available"
                    )
                )

    db.session.commit()

print("Seats generated successfully for screens 55–79!")

