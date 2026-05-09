from fastapi.testclient import TestClient

from app.main import app


def test_literature_detail_returns_item_by_id():
    client = TestClient(app)

    response = client.get("/api/literature/cn-ad-gbs-001")

    assert response.status_code == 200
    assert response.json() == {
        "id": "cn-ad-gbs-001",
        "title": "肠-脑-皮肤轴与特应性皮炎中医证候研究",
        "language": "zh",
        "source_type": "cn_literature",
        "source": "CNKI curated AD sample",
        "year": 2025,
        "snippet": "围绕特应性皮炎、肠-脑-皮肤轴与中医证候关联进行综述，强调脾虚湿蕴、血虚风燥等证候与皮肤屏障、神经免疫调节之间的联系。",
        "authors": ["王琳", "张倩", "刘晨"],
        "keywords": ["特应性皮炎", "肠-脑-皮肤轴", "中医证候", "皮肤屏障"],
        "evidence_tags": ["gut_skin_axis", "tcm_syndrome", "skin_barrier"],
        "abstract": "文章从肠-脑-皮肤轴视角讨论特应性皮炎的中医证候演变，提出脾虚湿蕴、血虚风燥与肠道微生态失衡、皮肤屏障异常和神经免疫调节紊乱之间存在可解释关联。",
        "citation_url": "https://example.org/cnki/cn-ad-gbs-001",
        "pubmed_id": None,
        "doi": None,
    }


def test_literature_detail_returns_404_for_unknown_id():
    client = TestClient(app)

    response = client.get("/api/literature/unknown")

    assert response.status_code == 404
    assert response.json() == {"detail": "Literature item not found"}
