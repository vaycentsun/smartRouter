"""任务分类器测试 — 合并 TaskTypeClassifier 与 TaskClassifier 测试"""

import pytest
from smart_router.classifier.task_classifier import TaskTypeClassifier, TaskTypeResult, TaskClassifier
from smart_router.classifier.types import ClassificationResult


class TestTaskTypeClassifier:
    """任务类型分类器测试"""
    
    @pytest.fixture
    def classifier(self):
        return TaskTypeClassifier({
            "writing": {
                "keywords": ["写", "文章", "邮件", "write", "draft"],
                "description": "写作任务"
            },
            "code_review": {
                "keywords": ["review", "审查", "代码", "code"],
                "description": "代码审查"
            },
            "chat": {
                "keywords": ["解释", "什么是", "explain", "what"],
                "description": "普通对话"
            }
        })
    
    def test_classify_writing(self, classifier):
        """测试写作任务分类"""
        messages = [{"role": "user", "content": "帮我写一封邮件"}]
        result = classifier.classify(messages)
        
        assert result.task_type == "writing"
        assert result.source == "keyword"
        assert result.confidence > 0
    
    def test_classify_code_review(self, classifier):
        """测试代码审查分类"""
        messages = [{"role": "user", "content": "review 这段代码"}]
        result = classifier.classify(messages)
        
        assert result.task_type == "code_review"
        assert result.source == "keyword"
    
    def test_classify_default_chat(self, classifier):
        """测试默认分类为 chat"""
        messages = [{"role": "user", "content": "随便说点什么"}]
        result = classifier.classify(messages)
        
        assert result.task_type == "chat"
        assert result.source == "default"
    
    def test_classify_empty_input(self, classifier):
        """测试空输入"""
        messages = [{"role": "user", "content": ""}]
        result = classifier.classify(messages)
        
        assert result.task_type == "chat"
        assert result.source == "default"
        assert result.confidence == 0.0


class TestTaskTypeClassifierWithKeywords:
    """TaskTypeClassifier 使用 keywords 的测试"""
    
    @pytest.fixture
    def classifier(self):
        return TaskTypeClassifier({
            "writing": {
                "keywords": ["写", "文章", "邮件", "write", "draft"],
                "examples": ["帮我写一封邮件", "起草一份报告"]
            },
            "code_review": {
                "keywords": ["review", "审查", "代码", "code"],
                "examples": ["review 这段代码"]
            },
            "chat": {
                "keywords": ["解释", "什么是", "explain", "what"],
                "examples": []
            }
        })
    
    def test_classify_by_keyword(self, classifier):
        """关键词匹配"""
        messages = [{"role": "user", "content": "帮我写一封邮件"}]
        result = classifier.classify(messages)
        
        assert result.task_type == "writing"
        assert result.source == "keyword"
        assert result.confidence > 0
    
    def test_classify_by_example(self, classifier):
        """示例相似度匹配"""
        messages = [{"role": "user", "content": "请帮我起草一份项目报告"}]
        result = classifier.classify(messages)
        
        assert result.task_type == "writing"
        assert result.source == "embedding"
    
    def test_classify_default(self, classifier):
        """默认分类"""
        messages = [{"role": "user", "content": "随便说点什么"}]
        result = classifier.classify(messages)
        
        assert result.task_type == "chat"
        assert result.source == "default"


class TestTaskClassifierWithKeywords:
    """使用 keywords 进行任务分类的测试"""
    
    @pytest.fixture
    def classifier_with_keywords(self):
        """创建带有 keywords 的分类器"""
        rules = [
            {
                "pattern": r"(?i)(写|文章|邮件|write|draft)",
                "task_type": "writing",
                "difficulty": "medium"
            },
            {
                "pattern": r"(?i)(review|审查|代码|code review)",
                "task_type": "code_review",
                "difficulty": "medium"
            },
            {
                "pattern": r"(?i)(解释|什么是|explain|what is)",
                "task_type": "explanation",
                "difficulty": "easy"
            },
        ]
        
        # 带有 keywords 的任务配置
        task_configs = {
            "writing": {
                "keywords": ["写", "文章", "邮件", "write", "draft", "起草", "撰写"],
                "examples": ["帮我写一封邮件", "起草一份报告", "写一篇技术博客"]
            },
            "code_review": {
                "keywords": ["review", "审查", "代码", "code", "检查", "bug", "优化"],
                "examples": ["review 这段代码", "检查一下这个函数", "找出代码里的 bug"]
            },
            "explanation": {
                "keywords": ["解释", "什么是", "explain", "what is", "怎么理解", "原理"],
                "examples": ["解释一下 Python 的 GIL", "什么是递归", "给我讲讲递归是什么", "帮我理解一下这个概念"]
            },
            "coding": {
                "keywords": ["写代码", "实现", "function", "class", "算法", "debug", "重构"],
                "examples": ["帮我写一个快速排序", "实现一个单例模式", "这段代码怎么优化"]
            },
        }
        
        return TaskClassifier(
            rules=rules,
            embedding_config={"enabled": True, "threshold": 0.6, "default_task": "chat"},
            task_configs=task_configs
        )
    
    def test_classify_by_keyword_hit(self, classifier_with_keywords):
        """关键词直接命中时应正确分类"""
        messages = [{"role": "user", "content": "帮我写一封求职邮件"}]
        result = classifier_with_keywords.classify(messages)
        
        assert result.task_type == "writing"
        assert result.source == "keyword"
        assert result.confidence > 0.5
    
    def test_classify_by_keyword_code_review(self, classifier_with_keywords):
        """代码审查关键词命中"""
        messages = [{"role": "user", "content": "review 一下这段代码有没有 bug"}]
        result = classifier_with_keywords.classify(messages)
        
        assert result.task_type == "code_review"
        assert result.source == "keyword"
    
    def test_classify_by_keyword_coding(self, classifier_with_keywords):
        """编程关键词命中"""
        # "实现" 和 "算法" 都是 coding 的明确关键词，不含 writing 的强关键词
        messages = [{"role": "user", "content": "实现一个二叉树遍历算法"}]
        result = classifier_with_keywords.classify(messages)
        
        assert result.task_type == "coding"
        assert result.source == "keyword"
    
    def test_classify_by_example_similarity(self, classifier_with_keywords):
        """无关键词命中时，通过 examples 相似度匹配"""
        # 文本与 coding 示例相似，但不包含任何明确的 keywords
        messages = [{"role": "user", "content": "来个快速排序吧"}]
        result = classifier_with_keywords.classify(messages)
        
        # 由于示例匹配，应该被分类为 coding
        assert result.task_type == "coding"
        assert result.source == "embedding"
    
    def test_classify_by_example_explanation(self, classifier_with_keywords):
        """通过 examples 相似度匹配 explanation"""
        messages = [{"role": "user", "content": "给我讲讲递归是什么"}]
        result = classifier_with_keywords.classify(messages)
        
        assert result.task_type == "explanation"
        assert result.source == "embedding"
    
    def test_keyword_priority_over_embedding(self, classifier_with_keywords):
        """关键词命中应优先于 embedding 匹配"""
        # "写" 是 writing 的关键词，但文本也有点像 coding
        messages = [{"role": "user", "content": "写一篇关于快速排序的文章"}]
        result = classifier_with_keywords.classify(messages)
        
        # keywords 应该优先
        assert result.task_type == "writing"
        assert result.source == "keyword"
    
    def test_classify_default_chat(self, classifier_with_keywords):
        """无匹配时应回退到 chat"""
        messages = [{"role": "user", "content": "今天天气怎么样"}]
        result = classifier_with_keywords.classify(messages)
        
        assert result.task_type == "chat"
        assert result.confidence < 0.5
    
    def test_classify_empty_input(self, classifier_with_keywords):
        """空输入应返回默认分类"""
        messages = [{"role": "user", "content": ""}]
        result = classifier_with_keywords.classify(messages)
        
        assert result.task_type == "chat"
        assert result.confidence == 0.0
    
    def test_classify_multiple_user_messages(self, classifier_with_keywords):
        """多个 user 消息应合并处理"""
        messages = [
            {"role": "user", "content": "你好"},
            {"role": "assistant", "content": "你好！有什么可以帮你的？"},
            {"role": "user", "content": "帮我review一下这段代码"}
        ]
        result = classifier_with_keywords.classify(messages)
        
        assert result.task_type == "code_review"


class TestTaskClassifierBackwardCompatibility:
    """向后兼容性测试：无 task_configs 时仍能正常工作"""
    
    def test_without_task_configs(self):
        """不传入 task_configs 时应使用旧的规则匹配"""
        rules = [
            {
                "pattern": r"(?i)(写|文章|邮件|write|draft)",
                "task_type": "writing",
                "difficulty": "medium"
            },
        ]
        
        classifier = TaskClassifier(
            rules=rules,
            embedding_config={"enabled": True, "threshold": 0.6, "default_task": "chat"}
        )
        
        messages = [{"role": "user", "content": "帮我写一篇文章"}]
        result = classifier.classify(messages)
        
        assert result.task_type == "writing"
        assert result.confidence > 0


class TestTaskClassifierDifficultyAdjustment:
    """测试 TaskClassifier 的难度升降档逻辑"""

    @pytest.fixture
    def task_classifier(self):
        return TaskClassifier(rules=[], embedding_config={})

    def test_bump_easy_to_medium(self, task_classifier):
        """easy 应升一档到 medium"""
        assert task_classifier._bump_difficulty("easy") == "medium"

    def test_bump_medium_to_hard(self, task_classifier):
        """medium 应升一档到 hard"""
        assert task_classifier._bump_difficulty("medium") == "hard"

    def test_bump_hard_to_expert(self, task_classifier):
        """hard 应升一档到 expert（V3 支持 4 档）"""
        assert task_classifier._bump_difficulty("hard") == "expert"

    def test_bump_expert_stays_expert(self, task_classifier):
        """expert 已最高档，应保持不变"""
        assert task_classifier._bump_difficulty("expert") == "expert"

    def test_lower_medium_to_easy(self, task_classifier):
        """medium 应降一档到 easy"""
        assert task_classifier._lower_difficulty("medium") == "easy"

    def test_lower_hard_to_medium(self, task_classifier):
        """hard 应降一档到 medium"""
        assert task_classifier._lower_difficulty("hard") == "medium"

    def test_lower_expert_to_hard(self, task_classifier):
        """expert 应降一档到 hard"""
        assert task_classifier._lower_difficulty("expert") == "hard"

    def test_lower_easy_stays_easy(self, task_classifier):
        """easy 已最低档，应保持不变"""
        assert task_classifier._lower_difficulty("easy") == "easy"
