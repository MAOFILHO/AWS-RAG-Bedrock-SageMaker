"""Golden sets under tests/golden/, each run through rag_course.ask with fake Bedrock. Live runs: -m live."""

import hashlib
import json
import shutil
from pathlib import Path

import pytest

import rag_course
from rag_course import core, pdf, sql
from rag_course.core import DONT_KNOW, NOT_ENOUGH_INFO, Settings
from rag_course.evaluate import holds
from fakes import echo_models, fake_models, fake_sql_models, saved_page

CHINOOK = Path(__file__).parents[1] / "data" / "Chinook.db"
FIXED = {"web": DONT_KNOW, "pdf": NOT_ENOUGH_INFO}
COUNTS = {"web": 6, "pdf": 6, "sql": 9, "generation": 5, "destructive_sql": 12, "out_of_scope": 3}


def golden(name: str) -> list[dict]:
    return json.loads((Path(__file__).parent / "golden" / f"{name}.json").read_text())


def cases(name: str):
    return pytest.mark.parametrize("case", golden(name), ids=lambda case: case["question"])


def ask(pipeline: str, case: dict, models) -> str:
    return rag_course.ask(pipeline, case["question"], models=models, fetch=saved_page, db=CHINOOK)


@pytest.mark.parametrize(
    ("answer", "expect", "ok"),
    [
        ("1,297 tracks", [1297], True),
        ("1297 tracks", [1297], True),
        ("12,970 tracks", [1297], False),
        ("Rock", ["Rock"], True),
    ],
)
def test_holds_ignores_thousands_separators(answer, expect, ok):
    assert holds(answer, expect) is ok


def test_employee_golden_accepts_an_answer_that_names_only_the_employee():
    case = next(c for c in golden("sql") if c["question"] == "Which employee supports the most customers?")
    assert holds("Jane Peacock supports the most customers.", case["expect"])


@pytest.mark.parametrize(("name", "count"), COUNTS.items())
def test_golden_file_holds_every_case(name, count):
    assert len(golden(name)) == count


@cases("web")
def test_web_golden_is_answered_from_its_saved_page(case):
    answer = ask("web", case, echo_models())
    assert holds(answer, case["expect"])
    assert holds(saved_page(case["source"]), case["expect"])


@cases("pdf")
def test_pdf_golden_is_answered_from_its_page(case):
    answer = ask("pdf", case, echo_models())
    assert holds(answer, case["expect"])
    assert holds(pdf.load_pdf(pdf.DEFAULT_PDF)[case["page"] - 1], case["expect"])


@cases("generation")
def test_generation_golden_answer_holds_its_key_facts(case):
    assert holds(ask(case["pipeline"], case, echo_models()), case["expect"])


@cases("out_of_scope")
def test_out_of_scope_golden_gets_the_fixed_sentence(case):
    assert ask(case["pipeline"], case, fake_models()) == FIXED[case["pipeline"]]


@cases("sql")
def test_sql_golden_is_answered_from_chinook(case):
    answer = ask("sql", case, fake_sql_models({case["question"]: case["sql"]}))
    assert holds(answer, case["expect"])


@cases("destructive_sql")
def test_destructive_golden_is_refused_and_the_database_is_unchanged(case, tmp_path):
    db = Path(shutil.copy(CHINOOK, tmp_path / "Chinook.db"))
    before = hashlib.sha256(db.read_bytes()).hexdigest()
    answer = rag_course.ask("sql", case["question"], models=fake_sql_models({case["question"]: case["sql"]}), db=db)
    assert answer == sql.REFUSAL
    assert hashlib.sha256(db.read_bytes()).hexdigest() == before


@pytest.mark.live
@cases("generation")
def test_live_generation_golden(case):
    models = core.bedrock_models(Settings.from_env())
    assert holds(rag_course.ask(case["pipeline"], case["question"], models=models), case["expect"])


@pytest.mark.live
@cases("out_of_scope")
def test_live_out_of_scope_golden(case):
    models = core.bedrock_models(Settings.from_env())
    assert rag_course.ask(case["pipeline"], case["question"], models=models) == FIXED[case["pipeline"]]


@pytest.mark.live
@cases("sql")
def test_live_sql_golden(case):
    models = core.bedrock_models(Settings.from_env())
    assert holds(rag_course.ask("sql", case["question"], models=models, db=CHINOOK), case["expect"])
