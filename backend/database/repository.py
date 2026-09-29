"""SQLite holds CRM records and delivery status, not recalled memories."""
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from backend.models import Deal, DealCreate, Interaction, InteractionCreate


class Repository:
    def __init__(self, path: Path):
        self.path = path

    @contextmanager
    def connection(self):
        connection = sqlite3.connect(self.path, timeout=15)
        connection.row_factory = sqlite3.Row
        connection.execute('PRAGMA foreign_keys=ON')
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def initialize(self, sample_path: Path | None):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS deals (
                    id TEXT PRIMARY KEY, payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS interactions (
                    id TEXT PRIMARY KEY, deal_id TEXT NOT NULL REFERENCES deals(id),
                    payload TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS interactions_deal ON interactions(deal_id);
                CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            ''')
            if sample_path and not db.execute("SELECT 1 FROM metadata WHERE key='seeded'").fetchone():
                for record in json.loads(sample_path.read_text(encoding='utf-8')):
                    deal = Deal.model_validate(record)
                    db.execute('INSERT OR IGNORE INTO deals VALUES (?, ?)',
                               (deal.id, deal.model_dump_json(exclude={'interactions'})))
                    for interaction in deal.interactions:
                        db.execute('INSERT OR IGNORE INTO interactions VALUES (?, ?, ?)',
                                   (interaction.id, deal.id, interaction.model_dump_json()))
                db.execute("INSERT INTO metadata VALUES ('seeded', 'true')")

    def list_deals(self) -> list[Deal]:
        with self.connection() as db:
            rows = db.execute('SELECT payload FROM deals ORDER BY rowid').fetchall()
            interactions = db.execute('SELECT payload FROM interactions').fetchall()
        grouped: dict[str, list[Interaction]] = {}
        for row in interactions:
            interaction = Interaction.model_validate_json(row['payload'])
            grouped.setdefault(interaction.deal_id, []).append(interaction)
        result = []
        for row in rows:
            deal = Deal.model_validate_json(row['payload'])
            deal.interactions = sorted(grouped.get(deal.id, []), key=lambda i: i.occurred_at, reverse=True)
            result.append(deal)
        return result

    def get_deal(self, deal_id: str) -> Deal | None:
        with self.connection() as db:
            row = db.execute('SELECT payload FROM deals WHERE id=?', (deal_id,)).fetchone()
            if not row:
                return None
            deal = Deal.model_validate_json(row['payload'])
            rows = db.execute('SELECT payload FROM interactions WHERE deal_id=?', (deal_id,)).fetchall()
        deal.interactions = sorted([Interaction.model_validate_json(r['payload']) for r in rows],
                                   key=lambda i: i.occurred_at, reverse=True)
        return deal

    def create_deal(self, data: DealCreate) -> Deal:
        deal = Deal(**data.model_dump(), id=str(uuid4()), created_at=datetime.now(timezone.utc).isoformat())
        with self.connection() as db:
            db.execute('INSERT INTO deals VALUES (?, ?)', (deal.id, deal.model_dump_json(exclude={'interactions'})))
        return deal

    def add_interaction(self, deal_id: str, data: InteractionCreate) -> Interaction:
        interaction = Interaction(**data.model_dump(), id=str(uuid4()), deal_id=deal_id)
        with self.connection() as db:
            db.execute('INSERT INTO interactions VALUES (?, ?, ?)',
                       (interaction.id, deal_id, interaction.model_dump_json()))
        return interaction

    def update_interaction(self, interaction: Interaction):
        with self.connection() as db:
            db.execute('UPDATE interactions SET payload=? WHERE id=?',
                       (interaction.model_dump_json(), interaction.id))
