"""Executable artifact DAG around the CAMEL producer Workforce and native agent stages.

CAMEL schedules the first three producer tasks. Downstream nodes execute their own
CAMEL agents only after these explicit, contract-checked dependencies are satisfied.
"""

import json
from pathlib import Path

from thesis_agents.agents.contracts import AGENT_CONTRACTS, TASK_DEPENDENCIES
from thesis_agents.canonical.agent import PREPARATION_CONTRACT
from thesis_agents.strategic.agent import NATIVE_STRATEGIC_CONTRACT
from thesis_agents.strategic.finalization_agent import FINALIZATION_CONTRACT
from thesis_agents.strategic.selection_agent import SELECTION_CONTRACT
from thesis_agents.strategic.validation_agent import VALIDATION_CONTRACT

NATIVE_DAG_CONTRACTS = (
    *AGENT_CONTRACTS[:3],
    PREPARATION_CONTRACT,
    NATIVE_STRATEGIC_CONTRACT,
    VALIDATION_CONTRACT,
    SELECTION_CONTRACT,
    FINALIZATION_CONTRACT,
)


def native_dependencies():
    producers = {artifact: c.task_id for c in NATIVE_DAG_CONTRACTS for artifact in c.outputs}
    # Operational profile is operator configuration, not an LLM-generated producer artifact.
    return {
        c.task_id: tuple(dict.fromkeys(producers[i] for i in c.inputs if i in producers))
        for c in NATIVE_DAG_CONTRACTS
    }


class NativeArtifactDAG:
    def __init__(self, output_dir, *, run_id, workflow):
        self.path = Path(output_dir) / "dag.json"
        self.dependencies = native_dependencies()
        if any(self.dependencies[k] != v for k, v in TASK_DEPENDENCIES.items() if k != "strategic"):
            raise ValueError("Source Workforce and native DAG dependencies differ")
        self.state = {
            "contract": "native-artifact-dag-v1",
            "run_id": run_id,
            "source_workflow": workflow,
            "scheduler": "camel-source-workforce-and-guarded-native-agents",
            "nodes": {
                c.task_id: {
                    "role": c.role,
                    "inputs": list(c.inputs),
                    "outputs": list(c.outputs),
                    "dependencies": list(self.dependencies[c.task_id]),
                    "status": "pending",
                }
                for c in NATIVE_DAG_CONTRACTS
            },
        }
        self._validators = {}
        self.save()

    def save(self):
        self.path.write_text(json.dumps(self.state, indent=2) + "\n")

    def _require_dependencies(self, task_id):
        for dep in self.dependencies[task_id]:
            if self.state["nodes"][dep]["status"] != "completed":
                raise ValueError(f"DAG prerequisite {dep} incomplete for {task_id}")
            self._validators[dep]()

    def complete_source(self, task_id, validator):
        """Record a CAMEL source publication only after checking its producer dependencies."""
        if task_id not in {c.task_id for c in AGENT_CONTRACTS[:3]}:
            raise ValueError("Not a source Workforce task")
        self._require_dependencies(task_id)
        validator()
        self._validators[task_id] = validator
        self.state["nodes"][task_id]["status"] = "completed"
        self.save()

    def execute(self, task_id, operation, validator):
        """Run an agent, then require its published artifact before releasing descendants."""
        node = self.state["nodes"][task_id]
        if node["status"] != "pending":
            raise ValueError("DAG node already executed or blocked")
        try:
            self._require_dependencies(task_id)
            node["status"] = "running"
            self.save()
            result = operation()
            validator()
            self._require_dependencies(task_id)
            self._validators[task_id] = validator
            node["status"] = "completed"
            self.save()
            return result
        except BaseException as exc:
            node.update(status="failed", error_type=type(exc).__name__)
            self.block_descendants(task_id)
            self.save()
            raise

    def block_descendants(self, failed):
        blocked = {failed}
        for task_id, node in self.state["nodes"].items():
            if node["status"] == "pending" and blocked.intersection(self.dependencies[task_id]):
                node.update(
                    status="blocked",
                    blocked_by=sorted(blocked.intersection(self.dependencies[task_id])),
                )
                blocked.add(task_id)

    def skip_native(self, reason):
        for contract in NATIVE_DAG_CONTRACTS[3:]:
            self.state["nodes"][contract.task_id].update(status="skipped", reason=reason)
        self.save()

    def fail_sources(self, validators):
        """Keep successful publications visible and block only actual failed descendants."""
        for task_id, validator in validators:
            if any(
                self.state["nodes"][d]["status"] != "completed" for d in self.dependencies[task_id]
            ):
                continue
            try:
                self.complete_source(task_id, validator)
            except (ValueError, OSError) as exc:
                self.state["nodes"][task_id].update(status="failed", error_type=type(exc).__name__)
                self.block_descendants(task_id)
        self.save()

    def assert_complete(self):
        for task_id, node in self.state["nodes"].items():
            if node["status"] != "completed":
                raise ValueError(f"DAG node incomplete: {task_id}")
            self._validators[task_id]()
