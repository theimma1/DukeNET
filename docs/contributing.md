# Contributing to DukeNET

Welcome to the DukeNET project! This guide will help you get started contributing to the AI Internet infrastructure.

---

## 🎯 Quick Start (5 Minutes)

### 1. Prerequisites

Required
Python 3.10+

Rust 1.70+

Go 1.21+

Node.js 18+

Docker & Docker Compose

Git

Check versions
python --version
rustc --version
go version
node --version
docker --version



### 2. Clone & Setup

Clone repository
git clone https://github.com/theimma1/DukeNET.git
cd DukeNET

Copy environment variables
cp .env.example .env

Start infrastructure services
docker-compose up -d

Verify services
docker-compose ps



### 3. Choose Your Component

DukeNET has 6 core components:

| Component | Language | Difficulty | Good First Issue |
| :--- | :--- | :--- | :--- |
| **AICP** (Protocol) | Rust + Python | Hard | No |
| **AINS** (Naming) | Go + Python | Medium | Yes |
| **AITP** (Tasks) | Python | Medium | Yes |
| **AgentOS** (Runtime) | Python | Medium | Yes |
| **Node Network** | Go + K8s | Hard | No |
| **Marketplace** | Python + React | Easy | Yes |

**New to DukeNET?** Start with **AITP** or **Marketplace**.

---

## 📚 Development Workflow

### 1. Create a Branch

Feature branch
git checkout -b feature/aitp-task-validation

Bug fix branch
git checkout -b fix/ains-search-bug

Documentation
git checkout -b docs/api-examples



### 2. Make Changes

Follow the coding standards for your component:

**Python:**
Install dependencies
cd packages/aitp-core/python
pip install -e ".[dev]"

Format code
black .

Lint
pylint aitp/

Run tests
pytest tests/



**Rust:**
cd packages/aicp-core/rust

Format
cargo fmt

Lint
cargo clippy

Test
cargo test



**Go:**
cd packages/ains-core/go

Format
go fmt ./...

Lint
golangci-lint run

Test
go test ./...



### 3. Commit with Conventional Commits

Format: <type>(<scope>): <description>
Examples:
git commit -m "feat(aitp): add task decomposition engine"
git commit -m "fix(ains): resolve search pagination bug"
git commit -m "docs(api): add AICP authentication examples"
git commit -m "test(aicp): add message signing tests"


**Types:** `feat`, `fix`, `docs`, `test`, `refactor`, `chore`

### 4. Push & Create PR

git push origin feature/aitp-task-validation



Then create a Pull Request on GitHub with:
- **Title:** Clear description of changes
- **Description:** What, why, and how
- **Tests:** Show tests pass
- **Screenshots:** If UI changes

---

## 🧪 Testing Standards

### Unit Tests (Required)

**Python:**
packages/aitp-core/python/tests/test_task.py
import pytest
from aitp.task import Task

def test_task_creation():
task = Task(name="Test", description="Test task")
assert task.name == "Test"
assert task.status == "PENDING"

def test_task_validation():
with pytest.raises(ValueError):
Task(name="", description="Invalid")



**Rust:**
// packages/aicp-core/rust/src/message.rs
#[cfg(test)]
mod tests {
use super::*;


#[test]
fn test_message_creation() {
    let msg = Message::new(MessageType::REQUEST);
    assert_eq!(msg.message_type, MessageType::REQUEST);
}
}



### Integration Tests (Recommended)

tests/integration/test_aicp_ains_integration.py
def test_agent_registration_and_lookup():
# Register agent via AICP
agent = register_agent("test_agent")


# Lookup via AINS
result = ains_client.get_agent(agent.agent_id)

assert result.agent_id == agent.agent_id


### Test Coverage Target

- **Minimum:** 80% line coverage
- **Target:** 90% line coverage
- **Critical paths:** 100% coverage

Check coverage (Python)
pytest --cov=aitp --cov-report=html tests/

Check coverage (Rust)
cargo tarpaulin --out Html



---

## 📖 Documentation Standards

### Code Comments

def decompose_task(task: Task, max_depth: int = 3) -> List[Subtask]:
"""Decompose a complex task into executable subtasks.


Args:
    task: The parent task to decompose
    max_depth: Maximum decomposition depth (default: 3)

Returns:
    List of subtasks with dependencies

Raises:
    ValueError: If task cannot be decomposed

Example:
    >>> task = Task(name="Research Paper Analysis")
    >>> subtasks = decompose_task(task)
    >>> len(subtasks) >= 1
    True
"""
pass


### Docstrings Required For

- All public functions
- All classes
- Complex algorithms
- API endpoints

---

## 🔒 Security Requirements

### Before Submitting PR

- [ ] No secrets in code (use environment variables)
- [ ] Input validation on all user inputs
- [ ] SQL queries use parameterized statements
- [ ] Dependencies scanned for vulnerabilities
- [ ] Authentication required for protected endpoints
- [ ] Rate limiting implemented

### Security Review Process

1. Automated security scan runs on PR
2. Manual review by security team (for sensitive changes)
3. Penetration testing (for major features)

---

## 🏗️ Architecture Guidelines

### Adding a New Feature

1. **Create ADR** (Architecture Decision Record)
cp docs/architecture/ADR-template.md docs/architecture/ADR-004-my-feature.md



2. **Design first, code second**
- Write specification
- Get feedback from team
- Then implement

3. **Follow existing patterns**
- Review similar code
- Use same structure
- Maintain consistency

---

## 🎓 Resources

### Documentation

- [AICP RFC](docs/protocols/AICP-RFC.md)
- [AINS Registry Schema](docs/protocols/AINS-Registry-Schema.md)
- [AITP Task Protocol](docs/protocols/AITP-Task-Protocol.md)
- [Database Schema](docs/architecture/Database-Schema.md)
- [Security Model](docs/architecture/Security-Model.md)
- [API Endpoints](docs/api/API-Endpoints.md)

### Tutorials

- [Build Your First Agent](docs/tutorials/build-your-first-agent.md)
- [Multi-Agent Workflow](docs/tutorials/multi-agent-workflow.md)
- [Marketplace Integration](docs/tutorials/marketplace-integration.md)

---

## 💬 Getting Help

- **Discord:** [DukeNET Community](https://discord.gg/dukenet) (coming soon)
- **GitHub Discussions:** [Ask questions](https://github.com/theimma1/DukeNET/discussions)
- **Email:** immanuel@dukenet.ai

---

## 📜 Contributor License Agreement (CLA)

All contributors must sign the [CLA](CLA.md) before their first PR is merged. This protects both you and the project.

---

**Thank you for contributing to DukeNET! 🚀**
