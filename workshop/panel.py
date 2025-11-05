
import json
import uuid
from typing import List
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox, QLabel, QLineEdit,
    QTextEdit, QPushButton, QListWidget, QTableWidget, QTableWidgetItem, QComboBox,
    QMessageBox, QCheckBox, QFileDialog, QScrollArea
)
from PyQt6.QtCore import Qt

from .models import Company, CompanyIntel, Person, Question, QuestionSet
from .questions.generator_gpt import GPTQuestionGenerator
from .background.simulator import ConversationSimulator
import yaml
from .utils.logger import get_logger
from pathlib import Path

LOGGER = get_logger("workshop.panel")

def _load_roles(path: str) -> List[str]:
    try:
        data = yaml.safe_load(open(path, "r", encoding="utf-8"))
        return [r.get("name","Other") for r in data.get("roles", [])]
    except Exception as e:
        LOGGER.error(f"Failed to load roles: {e}")
        return ["CEO","CFO","CTO","COO","CHRO","CIO","Other"]

ROLES = _load_roles(str(Path(__file__).with_name("config") / "roles.yaml"))

def _load_sample_company(path: str) -> Company:
    try:
        data = json.load(open(path, "r", encoding="utf-8"))
        c = data.get("company", {})
        company = Company(
            name=c.get("name","Acme Inc."),
            company_type=c.get("company_type","General"),
            purpose=c.get("purpose",""),
            key_info=c.get("key_info", []),
            objectives=c.get("objectives", []),
            intel=CompanyIntel(**c.get("intel", {})),
            people=[Person(name=p["name"], email=p["email"], role=p["role"]) for p in c.get("people", [])]
        )
        return company
    except Exception as e:
        LOGGER.error(f"Sample load failed: {e}")
        return Company()

class WorkshopSetupPanel(QWidget):
    """Drop-in QWidget implementing the Streamlit features, preserving host app theme."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.company = Company()
        self.qset = QuestionSet()
        self.qgen = GPTQuestionGenerator()
        self.sim = ConversationSimulator()
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        container = QWidget(); vbox = QVBoxLayout(container)

        # Load sample
        box = QGroupBox("Load Sample Data")
        hb = QHBoxLayout()
        self.btn_load_sample = QPushButton("Load Sample Data (Rising Pharma)")
        self.btn_load_sample.clicked.connect(self.on_load_sample)
        hb.addWidget(self.btn_load_sample)
        box.setLayout(hb); vbox.addWidget(box)

        # Key info
        vbox.addWidget(self._build_key_info())
        vbox.addWidget(self._build_objectives())
        vbox.addWidget(self._build_participants())
        vbox.addWidget(self._build_additional_info())
        vbox.addWidget(self._build_web_intel())
        vbox.addWidget(self._build_intel_summary())
        vbox.addWidget(self._build_generate_questions())

        scroll.setWidget(container)
        layout.addWidget(scroll)
        self.setLayout(layout)

    # --- Builders
    def _build_key_info(self):
        gb = QGroupBox("📝 Key Information")
        v = QVBoxLayout()
        grid = QGridLayout()
        grid.addWidget(QLabel("Company Name"),0,0); self.in_name = QLineEdit(); grid.addWidget(self.in_name,0,1)
        grid.addWidget(QLabel("Type/Industry"),1,0); self.in_type = QLineEdit(); grid.addWidget(self.in_type,1,1)
        grid.addWidget(QLabel("Purpose"),2,0); self.in_purpose = QLineEdit(); grid.addWidget(self.in_purpose,2,1)
        v.addLayout(grid)
        hb = QHBoxLayout(); self.in_key = QLineEdit(); self.in_key.setPlaceholderText("Add a key information item…")
        hb.addWidget(self.in_key); self.btn_add_key = QPushButton("➕ Add Key Info"); hb.addWidget(self.btn_add_key)
        self.btn_add_key.clicked.connect(self.on_add_key); self.list_key = QListWidget()
        v.addLayout(hb); v.addWidget(self.list_key); gb.setLayout(v); return gb

    def _build_objectives(self):
        gb = QGroupBox("🎯 Workshop Objectives")
        v = QVBoxLayout(); hb = QHBoxLayout()
        self.in_obj = QLineEdit(); self.in_obj.setPlaceholderText("Add an objective…")
        self.btn_add_obj = QPushButton("➕ Add Objective"); self.btn_add_obj.clicked.connect(self.on_add_objective)
        hb.addWidget(self.in_obj); hb.addWidget(self.btn_add_obj); self.list_obj = QListWidget()
        v.addLayout(hb); v.addWidget(self.list_obj); gb.setLayout(v); return gb

    def _build_participants(self):
        gb = QGroupBox("👥 Participants")
        v = QVBoxLayout()
        grid = QGridLayout()
        self.in_pname = QLineEdit(); self.in_pemail = QLineEdit(); self.in_prole = QComboBox(); self.in_prole.addItems(ROLES)
        grid.addWidget(QLabel("Name"),0,0); grid.addWidget(self.in_pname,0,1)
        grid.addWidget(QLabel("Email"),0,2); grid.addWidget(self.in_pemail,0,3)
        grid.addWidget(QLabel("Role"),0,4); grid.addWidget(self.in_prole,0,5)
        self.btn_add_person = QPushButton("➕ Add Participant"); self.btn_add_person.clicked.connect(self.on_add_participant)
        grid.addWidget(self.btn_add_person,0,6); v.addLayout(grid)
        self.tbl_people = QTableWidget(0,3); self.tbl_people.setHorizontalHeaderLabels(["Name","Email","Role"])
        self.tbl_people.horizontalHeader().setStretchLastSection(True)
        v.addWidget(self.tbl_people); gb.setLayout(v); return gb

    def _build_additional_info(self):
        gb = QGroupBox("🧰 Additional Company Information")
        v = QVBoxLayout(); self.txt_notes = QTextEdit(); self.txt_notes.setPlaceholderText("Additional notes…")
        v.addWidget(QLabel("Additional Notes:")); v.addWidget(self.txt_notes)
        self.btn_add_extra = QPushButton("➕ Add Extra Info"); self.btn_add_extra.clicked.connect(self.on_add_extra); v.addWidget(self.btn_add_extra)
        self.list_extras = QListWidget(); v.addWidget(self.list_extras); gb.setLayout(v); return gb

    def _build_web_intel(self):
        gb = QGroupBox("🔎 Web Intelligence Integrations")
        v = QHBoxLayout()
        self.btn_latest = QPushButton("🌐 Gather Latest Company Info")
        self.btn_financial = QPushButton("💹 Gather Financial Info")
        self.btn_comp = QPushButton("🏢 Gather Competitor Info")
        self.btn_latest.clicked.connect(self.on_fetch_latest)
        self.btn_financial.clicked.connect(self.on_fetch_financial)
        self.btn_comp.clicked.connect(self.on_fetch_competitors)
        v.addWidget(self.btn_latest); v.addWidget(self.btn_financial); v.addWidget(self.btn_comp)
        gb.setLayout(v); return gb

    def _build_intel_summary(self):
        gb = QGroupBox("📎 Company Intelligence Summary")
        grid = QGridLayout()
        self.out_latest = QTextEdit(); self.out_latest.setFixedHeight(90)
        self.out_financial = QTextEdit(); self.out_financial.setFixedHeight(90)
        self.out_comp = QTextEdit(); self.out_comp.setFixedHeight(90)
        for w in (self.out_latest,self.out_financial,self.out_comp):
            w.setReadOnly(False)
        grid.addWidget(QLabel("Latest:"),0,0); grid.addWidget(self.out_latest,0,1)
        grid.addWidget(QLabel("Financial:"),1,0); grid.addWidget(self.out_financial,1,1)
        grid.addWidget(QLabel("Competitors:"),2,0); grid.addWidget(self.out_comp,2,1)
        gb.setLayout(grid); return gb

    def _build_generate_questions(self):
        gb = QGroupBox("🟧 Generate Questions")
        v = QVBoxLayout()
        v.addWidget(QLabel("Step 1 — Desired Nature of Questions"))
        self.txt_nature = QTextEdit(); self.txt_nature.setPlainText("Strategic alignment, outcomes, risks, feasibility, and change management.")
        v.addWidget(self.txt_nature)
        hb = QHBoxLayout(); self.btn_generate = QPushButton("Generate / Refresh Questions"); self.btn_clear = QPushButton("Clear Questions")
        self.btn_generate.clicked.connect(self.on_generate_questions); self.btn_clear.clicked.connect(self.on_clear_questions)
        hb.addWidget(self.btn_generate); hb.addWidget(self.btn_clear); v.addLayout(hb)
        v.addWidget(QLabel("Step 3 — Review & Edit"))
        self.tbl_q = QTableWidget(0,5); self.tbl_q.setHorizontalHeaderLabels(["Category","Role","Text","Response","Score"]); self.tbl_q.horizontalHeader().setStretchLastSection(True)
        v.addWidget(self.tbl_q)
        self.chk_regen_notes = QCheckBox("Regenerate Questions using Notes (uses Additional Notes)"); v.addWidget(self.chk_regen_notes)
        self.chk_approve = QCheckBox("Approve Questions for Evaluation"); v.addWidget(self.chk_approve)
        v.addWidget(QLabel("Step 4 — Simulate Conversation & Score")); self.btn_sim = QPushButton("Run Simulation & Scoring"); self.btn_sim.clicked.connect(self.on_simulate); v.addWidget(self.btn_sim)
        gb.setLayout(v); return gb

    # --- Actions
    def on_load_sample(self):
        company = _load_sample_company(str(Path(__file__).with_name("config") / "sample_page1_data.json"))
        self.in_name.setText(company.name); self.in_type.setText(company.company_type); self.in_purpose.setText(company.purpose)
        self.list_key.clear(); [self.list_key.addItem(x) for x in company.key_info]
        self.list_obj.clear(); [self.list_obj.addItem(x) for x in company.objectives]
        self.tbl_people.setRowCount(0)
        for p in company.people:
            r = self.tbl_people.rowCount(); self.tbl_people.insertRow(r)
            self.tbl_people.setItem(r,0,QTableWidgetItem(p.name))
            self.tbl_people.setItem(r,1,QTableWidgetItem(p.email))
            self.tbl_people.setItem(r,2,QTableWidgetItem(p.role))
        self.out_latest.setPlainText(company.intel.latest or "")
        self.out_financial.setPlainText(company.intel.financial or "")
        self.out_comp.setPlainText(company.intel.competitors or "")
        self.list_extras.clear(); [self.list_extras.addItem(x) for x in (company.intel.extras or [])]

    def on_add_key(self):
        t = self.in_key.text().strip(); 
        if t: self.list_key.addItem(t); self.in_key.clear()

    def on_add_objective(self):
        t = self.in_obj.text().strip();
        if t: self.list_obj.addItem(t); self.in_obj.clear()

    def on_add_participant(self):
        name = self.in_pname.text().strip(); email = self.in_pemail.text().strip(); role = self.in_prole.currentText()
        if not name or not email:
            QMessageBox.warning(self, "Add Participant", "Name and Email are required."); return
        r = self.tbl_people.rowCount(); self.tbl_people.insertRow(r)
        self.tbl_people.setItem(r,0,QTableWidgetItem(name))
        self.tbl_people.setItem(r,1,QTableWidgetItem(email))
        self.tbl_people.setItem(r,2,QTableWidgetItem(role))
        self.in_pname.clear(); self.in_pemail.clear()

    def on_add_extra(self):
        t = self.txt_notes.toPlainText().strip()
        if t: self.list_extras.addItem(t); self.txt_notes.clear()

    def _collect_company(self) -> 'Company':
        key_info = [self.list_key.item(i).text() for i in range(self.list_key.count())]
        objectives = [self.list_obj.item(i).text() for i in range(self.list_obj.count())]
        people = []
        for r in range(self.tbl_people.rowCount()):
            name = self.tbl_people.item(r,0).text() if self.tbl_people.item(r,0) else ""
            email = self.tbl_people.item(r,1).text() if self.tbl_people.item(r,1) else ""
            role = self.tbl_people.item(r,2).text() if self.tbl_people.item(r,2) else ""
            if name and email: people.append(Person(name=name,email=email,role=role))
        extras = [self.list_extras.item(i).text() for i in range(self.list_extras.count())]
        intel = CompanyIntel(latest=self.out_latest.toPlainText().strip() or None,
                             financial=self.out_financial.toPlainText().strip() or None,
                             competitors=self.out_comp.toPlainText().strip() or None,
                             extras=extras)
        return Company(name=self.in_name.text().strip() or "Acme Inc.",
                       company_type=self.in_type.text().strip() or "General",
                       purpose=self.in_purpose.text().strip(),
                       key_info=key_info, objectives=objectives, intel=intel, people=people)

    def on_fetch_latest(self):
        from .integrations.web_intel import WebIntel
        c = self._collect_company()
        self.out_latest.setPlainText(WebIntel().fetch_latest(c.name, c.company_type))

    def on_fetch_financial(self):
        from .integrations.web_intel import WebIntel
        c = self._collect_company()
        self.out_financial.setPlainText(WebIntel().fetch_financial(c.name, c.company_type))

    def on_fetch_competitors(self):
        from .integrations.web_intel import WebIntel
        c = self._collect_company()
        self.out_comp.setPlainText(WebIntel().fetch_competitors(c.name, c.company_type))

    def on_generate_questions(self):
        c = self._collect_company(); nature = self.txt_nature.toPlainText()
        if self.chk_regen_notes.isChecked() and self.list_extras.count()>0:
            notes = [{"notes": self.list_extras.item(i).text()} for i in range(self.list_extras.count())]
            self.qset = self.qgen.regenerate_from_notes(c, nature, notes)
        else:
            self.qset = self.qgen.generate(c, nature)
        self._populate_questions()

    def _populate_questions(self):
        self.tbl_q.setRowCount(0)
        for q in self.qset.questions.values():
            r = self.tbl_q.rowCount(); self.tbl_q.insertRow(r)
            self.tbl_q.setItem(r,0,QTableWidgetItem(q.category))
            self.tbl_q.setItem(r,1,QTableWidgetItem(q.role or ""))
            self.tbl_q.setItem(r,2,QTableWidgetItem(q.text))
            self.tbl_q.setItem(r,3,QTableWidgetItem(q.response))
            self.tbl_q.setItem(r,4,QTableWidgetItem(f"{q.score:.2f}"))

    def on_clear_questions(self):
        self.qset = QuestionSet(); self.tbl_q.setRowCount(0); self.chk_approve.setChecked(False)

    def on_simulate(self):
        if not self.chk_approve.isChecked():
            QMessageBox.information(self, "Approve first", "Approve Questions for Evaluation to enable simulation."); return
        # pull table
        payload = []
        for r in range(self.tbl_q.rowCount()):
            payload.append({
                "category": self.tbl_q.item(r,0).text() if self.tbl_q.item(r,0) else "General",
                "role": self.tbl_q.item(r,1).text() if self.tbl_q.item(r,1) else None,
                "text": self.tbl_q.item(r,2).text() if self.tbl_q.item(r,2) else "",
            })
        c = self._collect_company()
        results = self.sim.simulate(c.dict(), payload)
        for i, res in enumerate(results):
            self.tbl_q.setItem(i,3,QTableWidgetItem(res.get("response","")))
            self.tbl_q.setItem(i,4,QTableWidgetItem(f"{float(res.get('score',0.0)):.2f}"))

    # Export is left to the host app; but provide a helper if needed
    def export_state(self, path: str):
        c = self._collect_company()
        export_questions = []
        for r in range(self.tbl_q.rowCount()):
            export_questions.append({
                "category": self.tbl_q.item(r,0).text() if self.tbl_q.item(r,0) else "",
                "role": self.tbl_q.item(r,1).text() if self.tbl_q.item(r,1) else None,
                "text": self.tbl_q.item(r,2).text() if self.tbl_q.item(r,2) else "",
                "response": self.tbl_q.item(r,3).text() if self.tbl_q.item(r,3) else "",
                "score": float(self.tbl_q.item(r,4).text()) if self.tbl_q.item(r,4) else 0.0
            })
        obj = {"company": c.dict(), "question_set":{"approved": self.chk_approve.isChecked(), "questions": export_questions}}
        with open(path, "w", encoding="utf-8") as f: json.dump(obj, f, ensure_ascii=False, indent=2)
