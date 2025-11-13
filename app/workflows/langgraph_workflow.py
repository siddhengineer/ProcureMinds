from typing import Any, TypedDict

from langgraph.graph import StateGraph, END


class WorkflowState(TypedDict):
    input_data: dict[str, Any]
    node_1_output: dict[str, Any]
    node_2_output: dict[str, Any]
    node_3_output: dict[str, Any]
    final_output: dict[str, Any]


class WorkflowGraph:
    def __init__(self):
        self.graph = self._build_graph()

    async def node_1(self, state: WorkflowState) -> WorkflowState:
        """First async node in the workflow."""
        result = {"processed": True, "data": state["input_data"]}
        state["node_1_output"] = result
        return state

    async def node_2(self, state: WorkflowState) -> WorkflowState:
        """Second async node in the workflow."""
        result = {"enhanced": True, "previous": state["node_1_output"]}
        state["node_2_output"] = result
        return state

    async def node_3(self, state: WorkflowState) -> WorkflowState:
        """Third async node in the workflow."""
        result = {"finalized": True, "previous": state["node_2_output"]}
        state["node_3_output"] = result
        return state

    async def final_node(self, state: WorkflowState) -> WorkflowState:
        """Final async node that aggregates results."""
        state["final_output"] = {
            "node_1": state["node_1_output"],
            "node_2": state["node_2_output"],
            "node_3": state["node_3_output"],
        }
        return state

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow."""
        workflow = StateGraph(WorkflowState)

        workflow.add_node("node_1", self.node_1)
        workflow.add_node("node_2", self.node_2)
        workflow.add_node("node_3", self.node_3)
        workflow.add_node("final_node", self.final_node)

        workflow.set_entry_point("node_1")
        workflow.add_edge("node_1", "node_2")
        workflow.add_edge("node_2", "node_3")
        workflow.add_edge("node_3", "final_node")
        workflow.add_edge("final_node", END)

        return workflow.compile()

    async def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Execute the workflow with given input data."""
        initial_state: WorkflowState = {
            "input_data": input_data,
            "node_1_output": {},
            "node_2_output": {},
            "node_3_output": {},
            "final_output": {},
        }
        result = await self.graph.ainvoke(initial_state)
        return result["final_output"]
