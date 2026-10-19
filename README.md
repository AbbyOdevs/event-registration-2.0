# Event Registration System

CMSC 203 – Object-Oriented Programming · Final Project  
A Flask web application where students register for College of Computer Studies events and an administrator manages events, participants and attendance.

## Run it
```
pip install -r requirements.txt
python app.py            # http://localhost:5000
```
Set these environment variables before deploying: `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `SECRET_KEY`
(defaults for local development: `admin@gatehub.local` / `gate2026`).
Data is saved in `data.json` (created automatically; do not commit it).

## Run the tests
```
python -m unittest discover -s tests -v
```

## Project structure
| Path | Purpose |
|---|---|
| `app.py` | Application factory and entry point |
| `config.py` | Settings read from environment variables |
| `exceptions.py` | Custom exception hierarchy (`EventSystemError` and subclasses) |
| `validation.py` | Reusable input-validation helpers |
| `models/` | OOP domain classes: `Entity`, `Person`, `Participant`, `Admin`, `Event`, `Registration`, `Database` |
| `repository.py` | Abstract `Repository` and `JsonRepository` (save/load `data.json`) |
| `services/` | Business rules: `AuthService`, `EventService`, `RegistrationService` |
| `routes.py` | Thin Flask routes that call the services |
| `templates/`, `static/` | The user interface (HTML, CSS, JavaScript) |
| `tests/` | Automated tests |
| `docs/` | UML class diagram, flowcharts, screenshots, documentation |

## OOP concepts used
Classes/objects, constructors, encapsulation (private attributes + validated properties), inheritance (`Entity → Person → Participant/Admin`), polymorphism (`describe()`, `to_dict()`, `check_password()`), abstraction (abstract `Entity`, `Person`, `Repository`), method overloading (`EventService.get` accepts an id or an `Event` via `singledispatchmethod`; default arguments), custom exceptions.
