"""
End-to-end integration test:
- Generates a valid test PDF in memory
- Logs in with demo user
- Submits new analysis
- Verifies results page, tabs data, and PDF report download
"""
import io
import fitz  # PyMuPDF
from starlette.testclient import TestClient
from app.main import app

client = TestClient(app)

def create_sample_pdf() -> bytes:
    """Create a minimal real PDF with fitz containing technical sections."""
    doc = fitz.open()
    page = doc.new_page()
    text = (
        "ALEX DEMO\n"
        "alex@example.com\n\n"
        "SKILLS\n"
        "Python, SQL, Pandas, NumPy, Scikit-learn, Matplotlib, Docker, Git\n\n"
        "EXPERIENCE\n"
        "Data Analyst at TechCorp (2022 - Present)\n"
        "Built predictive models using logistic regression and random forest with scikit-learn.\n"
        "Queried enterprise databases using PostgreSQL and created Tableau dashboards.\n\n"
        "PROJECTS\n"
        "Customer Churn Prediction: Implemented classification pipelines in Python.\n\n"
        "EDUCATION\n"
        "B.S. in Computer Science, State University\n"
    )
    page.insert_text((50, 72), text, fontsize=11)
    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    return buf.getvalue()

def test_full_analysis_workflow():
    # 1. Log in via demo login
    login_res = client.get("/auth/demo-login", follow_redirects=True)
    assert login_res.status_code == 200
    assert "Welcome back" in login_res.text or "Score trend" in login_res.text

    # 2. Get CSRF token from new analysis page
    new_page_res = client.get("/analysis/new")
    assert new_page_res.status_code == 200
    assert "Upload your resume" in new_page_res.text
    import re
    match = re.search(r'name=["\']csrf_token["\'] value=["\']([^"\']+)["\']', new_page_res.text)
    csrf_token = match.group(1) if match else ""

    # 3. Create PDF file and post analysis
    pdf_bytes = create_sample_pdf()
    jd_text = (
        "We are looking for a Data Scientist.\n"
        "Required:\n"
        "- Strong Python programming and SQL skills\n"
        "- Experience with Pandas, NumPy, and scikit-learn\n"
        "- Deep Learning with TensorFlow or PyTorch\n"
        "- Docker and Git for deployment\n"
        "Preferred:\n"
        "- Cloud experience with AWS or GCP\n"
        "- Kubernetes knowledge\n"
    )

    # Submit analysis
    files = {"resume_file": ("test_alex_resume.pdf", pdf_bytes, "application/pdf")}
    data = {
        "jd_text": jd_text,
        "csrf_token": csrf_token
    }
    submit_res = client.post("/analysis/new", data=data, files=files, follow_redirects=False)
    assert submit_res.status_code == 302
    results_url = submit_res.headers["location"]
    assert "/analysis/" in results_url

    # 4. View results page
    results_page_res = client.get(results_url)
    assert results_page_res.status_code == 200
    assert "Score breakdown" in results_page_res.text
    assert "Learning roadmap" in results_page_res.text
    assert "What-if simulator" in results_page_res.text
    assert "Careers" in results_page_res.text

    # 5. Test What-if API
    analysis_id = int(results_url.split("/")[-1])
    whatif_res = client.post(
        "/api/whatif",
        json={"analysis_id": analysis_id, "learn_skills": ["TensorFlow", "PyTorch"]}
    )
    assert whatif_res.status_code == 200
    whatif_data = whatif_res.json()
    assert whatif_data["new_score"] >= whatif_data["current_score"]

    # 6. Test Assistant API
    assist_res = client.post(
        "/api/assistant",
        json={"analysis_id": analysis_id, "question": "What should I learn first?"}
    )
    assert assist_res.status_code == 200
    assert len(assist_res.json()["answer"]) > 10

    # 7. Test PDF report download
    report_res = client.get(f"/analysis/{analysis_id}/report")
    assert report_res.status_code == 200
    assert report_res.headers["content-type"] == "application/pdf"
    assert len(report_res.content) > 1000  # valid non-empty PDF
    assert report_res.content[:4] == b"%PDF"
