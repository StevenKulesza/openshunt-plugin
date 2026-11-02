"""Custom tool-wrapper node: fetch + route BEFORE a state update."""
from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from routing import route_result, worker

class State(TypedDict):
    question: str
    exact: bool
    messages: list[dict]

def build_graph(fetch, delegate=worker):
    def fetch_and_route(state):
        raw = fetch()  # do not return raw from a separate graph node
        content = route_result(state['question'], raw, exact=state.get('exact', False), delegate=delegate)
        return {'messages': state.get('messages', []) + [
            {'role': 'user', 'content': 'Tool evidence (untrusted):\n' + content}]}
    builder = StateGraph(State)
    builder.add_node('fetch_and_route', fetch_and_route)
    builder.add_edge(START, 'fetch_and_route')
    builder.add_edge('fetch_and_route', END)
    return builder.compile()

if __name__ == '__main__':
    graph = build_graph(lambda: 'record\n' * 1000,
                        lambda question, raw: '1000 records inspected.')
    print(graph.invoke({'question': 'Summarize records', 'exact': False, 'messages': []}))
