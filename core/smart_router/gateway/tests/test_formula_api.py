"""Dashboard Formula API 测试"""

import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from smart_router.gateway.dashboard_api import build_dashboard_app


class TestFormulaAPI:
    """测试公式配置 API 端点"""

    @pytest.fixture
    def temp_config_dir(self, tmp_path):
        """创建临时配置目录"""
        config_dir = tmp_path / ".smart-router"
        config_dir.mkdir()
        
        # providers.yaml
        providers = {
            "providers": {
                "openai": {
                    "api_base": "https://api.openai.com/v1",
                    "api_key": "sk-test"
                }
            }
        }
        import yaml
        with open(config_dir / "providers.yaml", "w") as f:
            yaml.safe_dump(providers, f)
        
        # models/
        models_dir = config_dir / "models"
        models_dir.mkdir()
        models = {
            "models": {
                "gpt-4o": {
                    "provider": "openai",
                    "litellm_model": "openai/gpt-4o",
                    "capabilities": {
                        "quality": 9,
                        "cost": 3,
                        "context": 128000
                    },
                    "supported_tasks": ["chat"],
                    "difficulty_support": ["easy", "medium", "hard"]
                },
                "gpt-4o-mini": {
                    "provider": "openai",
                    "litellm_model": "openai/gpt-4o-mini",
                    "capabilities": {
                        "quality": 6,
                        "cost": 9,
                        "context": 128000
                    },
                    "supported_tasks": ["chat"],
                    "difficulty_support": ["easy", "medium"]
                }
            }
        }
        with open(models_dir / "test.yaml", "w") as f:
            yaml.safe_dump(models, f)
        
        # routing.yaml
        routing = {
            "tasks": {
                "chat": {
                    "name": "Chat",
                    "description": "Chat task",
                    "capability_weights": {"quality": 0.6, "cost": 0.4}
                }
            },
            "difficulties": {
                "easy": {"description": "Easy", "max_tokens": 1000},
                "medium": {"description": "Medium", "max_tokens": 4000}
            },
            "strategies": {
                "auto": {"description": "Auto"}
            },
            "fallback": {
                "mode": "auto",
                "similarity_threshold": 2,
                "provider_isolation": False,
                "max_attempts": 3
            }
        }
        with open(config_dir / "routing.yaml", "w") as f:
            yaml.safe_dump(routing, f)
        
        return config_dir

    @pytest.fixture
    def client(self, temp_config_dir, monkeypatch):
        """创建 TestClient，使用临时配置目录"""
        monkeypatch.setattr(
            "smart_router.gateway.dashboard_api.Path.home",
            lambda: temp_config_dir.parent
        )
        app = build_dashboard_app()
        return TestClient(app)

    def test_get_formula(self, client):
        """GET /api/formula 返回当前 weights"""
        response = client.get("/api/formula")
        assert response.status_code == 200
        data = response.json()
        assert "weights" in data
        # 旧配置已自动迁移为全局 formula
        assert "quality" in data["weights"]
        assert "cost" in data["weights"]

    def test_update_formula_success(self, client):
        """PUT /api/formula 更新成功"""
        response = client.put(
            "/api/formula",
            json={"weights": {"quality": 0.8, "cost": 0.2}}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        
        # 验证更新后 GET 返回新值
        response = client.get("/api/formula")
        data = response.json()
        assert data["weights"]["quality"] == 0.8
        assert data["weights"]["cost"] == 0.2

    def test_update_formula_invalid_weight(self, client):
        """PUT /api/formula 传入无效权重返回错误"""
        response = client.put(
            "/api/formula",
            json={"weights": {"quality": 1.5, "cost": 0.2}}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert len(data["errors"]) > 0

    def test_update_formula_unknown_dimension(self, client):
        """PUT /api/formula 传入未知维度返回错误"""
        response = client.put(
            "/api/formula",
            json={"weights": {"quality": 0.5, "unknown_dim": 0.5}}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False

    def test_preview_formula(self, client):
        """POST /api/formula/preview 返回模型得分排序"""
        response = client.post(
            "/api/formula/preview",
            json={"weights": {"quality": 0.9, "cost": 0.1}, "prompt": "test"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "models" in data
        assert len(data["models"]) == 2
        
        # 按 quality 优先，gpt-4o (quality=9) 应该排第一
        models = data["models"]
        assert models[0]["name"] == "gpt-4o"
        assert models[0]["score"] > models[1]["score"]

    def test_preview_formula_invalid_weight(self, client):
        """POST /api/formula/preview 传入无效权重返回 400"""
        response = client.post(
            "/api/formula/preview",
            json={"weights": {"quality": -0.5}, "prompt": "test"}
        )
        assert response.status_code == 400

    def test_preview_formula_cost_priority(self, client):
        """POST /api/formula/preview 成本优先时 gpt-4o-mini 排第一"""
        response = client.post(
            "/api/formula/preview",
            json={"weights": {"quality": 0.1, "cost": 0.9}, "prompt": "test"}
        )
        assert response.status_code == 200
        data = response.json()
        models = data["models"]
        # cost 优先：gpt-4o-mini (cost=9) > gpt-4o (cost=3)
        assert models[0]["name"] == "gpt-4o-mini"
