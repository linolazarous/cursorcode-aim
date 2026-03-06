"""
CursorCode AI
Task Dependency Graph

Executes project tasks in correct dependency order.
"""

import logging
from typing import Dict, List

logger = logging.getLogger("ai_task_graph")


class TaskGraph:

    def __init__(self):
        self.tasks = []
        self.dependencies = {}

    def add_task(self, task_id: str, name: str):
        self.tasks.append({"id": task_id, "name": name})
        self.dependencies[task_id] = []

    def add_dependency(self, task_id: str, depends_on: str):
        if task_id not in self.dependencies:
            self.dependencies[task_id] = []

        self.dependencies[task_id].append(depends_on)

    def resolve_execution_order(self) -> List[str]:
        """
        Topological sorting
        """

        visited = set()
        order = []

        def visit(task):
            if task in visited:
                return

            for dep in self.dependencies.get(task, []):
                visit(dep)

            visited.add(task)
            order.append(task)

        for task in self.dependencies:
            visit(task)

        return order


def build_default_graph() -> TaskGraph:
    """
    Standard AI project execution pipeline
    """

    graph = TaskGraph()

    graph.add_task("architecture", "System Architecture")
    graph.add_task("backend", "Backend Development")
    graph.add_task("frontend", "Frontend Development")
    graph.add_task("security", "Security Audit")
    graph.add_task("tests", "Testing")
    graph.add_task("devops", "Deployment")

    graph.add_dependency("backend", "architecture")
    graph.add_dependency("frontend", "architecture")
    graph.add_dependency("security", "backend")
    graph.add_dependency("tests", "backend")
    graph.add_dependency("devops", "backend")

    logger.info("Task graph initialized")

    return graph
