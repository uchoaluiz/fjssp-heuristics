import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib.patches as mpatches

from itertools import combinations
from pathlib import Path

from ..instance.instance import Instance
from .crono import Crono


class DAG:
    def __init__(self, instance: Instance):
        self._instance = instance
        self._graph = nx.DiGraph()
        self._positions = dict()
        self._disjunctive_visuals = dict()
        self._edge_weights = dict()

        self._build_base_graph()

    @property
    def graph(self):
        return self._graph

    def set_edge_weight(self, from_node: int, to_node: int, weight: float):
        self._edge_weights[(from_node, to_node)] = weight
        if self._graph.has_edge(from_node, to_node):
            self._graph[from_node][to_node]["weight"] = weight

    def _build_base_graph(self):
        instance = self._instance

        # adds nodes
        for job, ops in instance.S_j.items():
            for i, op in enumerate(ops):
                self._add_operation(op=op, pos_x=i, pos_y=job)

        # adds edges
        for job in instance.P_j:
            for _from, _to in job:
                self._add_dependency(from_node=_from, to_node=_to)

        # adds nodes & edges for artificial nodes 'S' and 'T'
        self._add_artificial_nodes()

    def _add_operation(self, *, op: int, pos_x: float, pos_y: float):
        self._graph.add_node(op)
        self._positions[op] = (pos_x, -pos_y)

    def _add_dependency(self, *, from_node: int, to_node: int, weight="?"):
        self._graph.add_edge(from_node, to_node, weight=weight)
        self._edge_weights[(from_node, to_node)] = weight

    def _add_artificial_nodes(self):
        instance = self._instance
        y_values = range(instance.num_jobs)
        center_y = 0 if not y_values else -y_values[len(y_values) // 2]

        self._graph.add_node("S")
        self._graph.add_node("V")

        min_x = min(pos[0] for pos in self._positions.values())
        max_x = max(pos[0] for pos in self._positions.values())
        self._positions["S"] = (min_x - 1, center_y)
        self._positions["V"] = (max_x + 1, center_y)

        for ops in instance.S_j.values():
            self._add_dependency(from_node="S", to_node=ops[0])
            self._add_dependency(from_node=ops[-1], to_node="V")

    def add_visual_disjunctive_edge(self, machine: int, from_node: int, to_node: int):
        self._disjunctive_visuals.setdefault(machine, []).append((from_node, to_node))

    def draw(
        self,
        *,
        output_path: Path,
        title: str,
        show_disjunct: bool = False,
        arrowstyle: str = "->",
        time_limit: float = 10.0,
    ):
        timer = Crono()

        try:
            plt.figure(figsize=(12, 6))

            nx.draw_networkx_nodes(
                self._graph, pos=self._positions, node_color="lightblue", node_size=300
            )
            nx.draw_networkx_labels(
                self._graph, pos=self._positions, font_size=10, font_weight="bold"
            )

            if timer.elapsed_time() > time_limit:
                raise TimeoutError("time exceeded in creating nodes (operations)")

            nx.draw_networkx_edges(
                self._graph,
                pos=self._positions,
                edge_color="black",
                arrows=True,
                arrowsize=10,
            )

            if timer.elapsed_time() > time_limit:
                raise TimeoutError("time exceeded in creating the edges")

            edge_labels = {
                (u, v): f"{self._edge_weights.get((u, v), '')}"
                for u, v in self._graph.edges()
            }
            nx.draw_networkx_edge_labels(
                self._graph,
                pos=self._positions,
                edge_labels=edge_labels,
                font_color="red",
                font_size=8,
            )

            if timer.elapsed_time() > time_limit:
                raise TimeoutError("time exceeded in evaluating the edges")

            if show_disjunct:
                color_map = cm.get_cmap("tab10")
                machines = list(self._disjunctive_visuals.keys())
                n_colors = len(machines)

                for i, machine in enumerate(machines):
                    if timer.elapsed_time() > time_limit:
                        raise TimeoutError(
                            "time exceeded in creating the visual disjunctive edges"
                        )

                    color = color_map(i / max(n_colors - 1, 1))
                    arcs = self._disjunctive_visuals[machine]
                    rad = 0.2 + (i % 3) * 0.2
                    mult = 1

                    for edge in arcs:
                        edge_rad = rad * 1.3 * mult
                        nx.draw_networkx_edges(
                            self._graph,
                            pos=self._positions,
                            edgelist=[edge],
                            edge_color=[color],
                            style="dashed",
                            arrows=True,
                            arrowstyle=arrowstyle,
                            arrowsize=20,
                            width=2,
                            connectionstyle=f"arc3,rad={edge_rad}",
                        )
                        mult *= -1

                legend_patches = [
                    mpatches.FancyArrowPatch(
                        (0, 0),
                        (1, 0),
                        connectionstyle="arc3,rad=0.0",
                        color="black",
                        label="Sequência Tecnológica",
                    )
                ]

                for i, machine in enumerate(machines):
                    color = color_map(i / max(n_colors - 1, 1))
                    patch = mpatches.FancyArrowPatch(
                        (0, 0),
                        (1, 0),
                        connectionstyle="arc3,rad=0.2",
                        linestyle="dashed",
                        color=color,
                        label=f"Máquina {machine}",
                    )
                    legend_patches.append(patch)

                plt.legend(
                    handles=legend_patches,
                    loc="lower center",
                    bbox_to_anchor=(0.5, -0.1),
                    ncol=3,
                    frameon=False,
                    fontsize=9,
                )

            suffix = "with" if show_disjunct else "without"
            plt.title(f"{title} - {suffix} disjunctives")
            plt.axis("off")
            plt.tight_layout()

            if timer.elapsed_time() > time_limit:
                raise TimeoutError("time exceeded in final layout")

            plt.savefig(output_path / f"{title} - {suffix} disjunctive.png")
            plt.close()
        except TimeoutError as e:
            plt.close()

            print(f"[WARNING]: {str(e)}.")
            print("DAG wasn't wrote because of its excessive flexibility.")
            print(
                "you can try using a greater time_limit parameter on method 'export_visualization()'\n"
            )

            return False


class FJSSPGraph:
    def __init__(
        self,
        *,
        instance: Instance,
        machines_assignment: list[list[int]],
        tech_disjunc: bool = False,
    ):
        self._instance = instance
        self._machines_assignment = machines_assignment
        self._dag = DAG(instance)

        self._create_visual_disjunctives(tech_disjunc=tech_disjunc)
        self._set_edge_weights()

    def _create_visual_disjunctives(self, *, tech_disjunc: bool = False):
        for machine, ops in enumerate(self._machines_assignment):
            for op1, op2 in combinations(ops, 2):
                if tech_disjunc or (
                    self._instance.job_of_op[op1] != self._instance.job_of_op[op2]
                ):
                    self._dag.add_visual_disjunctive_edge(machine, op1, op2)

    def _set_edge_weights(self):
        def _are_operations_assigned() -> bool:
            all_ops = [
                op for machine_seq in self._machines_assignment for op in machine_seq
            ]
            return len(all_ops) == len(set(all_ops))

        if _are_operations_assigned():
            instance = self._instance
            for u, v in self._dag.graph.edges():
                if u not in ["S", "V"] and v not in ["S"]:
                    machine = next(
                        (
                            m
                            for m, ops in enumerate(self._machines_assignment)
                            if u in ops
                        ),
                        None,
                    )
                    if machine is not None:
                        weight = instance.p[(u, machine)]
                        self._dag.set_edge_weight(u, v, weight)
                if u == "S":
                    self._dag.set_edge_weight(u, v, 0)
        else:
            if u == "S":
                self._dag.set_edge_weight(u, v, 0)

    def add_disjunctive_dependency(
        self, from_node: int, to_node: int, machine: int, weight: float
    ):
        weight = self._instance.p[(from_node, machine)]
        self._dag.graph.add_edge(from_node, to_node, weight=weight)
        self._dag.set_edge_weight(from_node, to_node, weight)

    def consolidate_sequence_on_machine(self, machine_id: int, sequence: list[int]):
        for i in range(len(sequence) - 1):
            from_op = sequence[i]
            to_op = sequence[i + 1]
            if self._instance.job_of_op[from_op] != self._instance.job_of_op[to_op]:
                self.add_disjunctive_dependency(
                    from_op,
                    to_op,
                    machine_id,
                    weight=self._instance.p[(from_op, machine_id)],
                )

    def longest_path_to(self, op: int) -> float:
        subgraph = self._dag.graph.subgraph(nx.ancestors(self._dag.graph, op) | {op})
        return nx.dag_longest_path_length(subgraph, weight="weight")

    def longest_path_from(self, op: int) -> float:
        subgraph = self._dag.graph.subgraph(nx.descendants(self._dag.graph, op) | {op})
        return nx.dag_longest_path_length(subgraph, weight="weight")

    def draw_dag(
        self,
        output_path: Path,
        title: str,
        show_disjunct: bool = True,
        arrowstyle: str = "->",
        time_limit: float = 10.0,
    ):
        self._dag.draw(
            output_path=output_path,
            title=title,
            show_disjunct=show_disjunct,
            arrowstyle=arrowstyle,
            time_limit=time_limit,
        )

    def export_visualization(
        self,
        output_path: Path,
        title: str,
        arrowstyle: str = "->",
        show: str = "disjunctives",
        time_limit: float = 10.0,
    ):
        if show in ["connectives", "both"]:
            self.draw_dag(
                output_path,
                title,
                show_disjunct=False,
                arrowstyle=arrowstyle,
                time_limit=time_limit,
            )
        if show in ["disjunctives", "both"]:
            self.draw_dag(
                output_path,
                title,
                show_disjunct=True,
                arrowstyle=arrowstyle,
                time_limit=time_limit,
            )
