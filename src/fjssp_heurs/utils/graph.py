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
        self._disjunctive_edges = dict()

        self._build_base_graph()

    def _build_base_graph(self):
        instance = self._instance

        # adds nodes
        for job, ops in instance.S_j.items():
            for i, op in enumerate(ops):
                self._add_operation(op=op, pos_x=i * 2, pos_y=job * 4)

        # adds edges
        for job in instance.P_j:
            for _from, _to in job:
                self._add_dependency(from_node=_from, to_node=_to)

        # adds nodes & edges for artificial nodes 'S' and 'T'
        self._add_artificial_nodes()

    def set_edge_weight(self, from_node: int, to_node: int, weight: float):
        if self._graph.has_edge(from_node, to_node):
            self._graph[from_node][to_node]["weight"] = weight
        else:
            print(f"edge ({from_node}, {to_node}) not in graph.edges")

    def _add_operation(self, *, op: int, pos_x: float, pos_y: float):
        self._graph.add_node(op)
        self._positions[op] = (pos_x, -pos_y)

    def _add_dependency(self, *, from_node: int, to_node: int, weight=0):
        self._graph.add_edge(from_node, to_node, weight=weight)

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

    def add_disjunctive_edge(
        self,
        machine: int,
        from_node: int,
        to_node: int,
        weight: int = 0,
        consolidated: bool = True,
    ):
        if consolidated:
            self._graph.add_edge(from_node, to_node, weight=weight)
        self._disjunctive_edges.setdefault(machine, []).append((from_node, to_node))

    def draw(
        self,
        *,
        output_path: Path,
        title: str,
        show_visual_disjunct: bool = False,
        show_real_disjunct: bool = False,
        arrowstyle: str = "->",
        time_limit: float = 10.0,
    ):
        timer = Crono()

        try:
            plt.figure(figsize=(16, 10))

            nx.draw_networkx_nodes(
                self._graph, pos=self._positions, node_color="lightblue", node_size=300
            )
            nx.draw_networkx_labels(
                self._graph, pos=self._positions, font_size=10, font_weight="bold"
            )

            if timer.elapsed_time() > time_limit:
                raise TimeoutError("time exceeded in creating nodes (operations)")

            if not show_real_disjunct:
                added_disjunctive_edges = [
                    edge
                    for edges_in_machine in self._disjunctive_edges.values()
                    for edge in edges_in_machine
                ]
                all_tech_edges = [
                    edge for job_edges in self._instance.P_j for edge in job_edges
                ]

                unwanted_edges = [
                    edge
                    for edge in added_disjunctive_edges
                    if edge not in all_tech_edges
                ]
                showing_edges = [
                    e for e in self._graph.edges if e not in unwanted_edges
                ]
            else:
                showing_edges = self._graph.edges

            nx.draw_networkx_edges(
                self._graph,
                pos=self._positions,
                edgelist=showing_edges,
                edge_color="black",
                arrows=True,
                arrowsize=10,
            )

            if timer.elapsed_time() > time_limit:
                raise TimeoutError("time exceeded in creating the edges")

            edge_labels = {
                (u, v): self._graph[u][v]["weight"] for u, v in showing_edges
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

            if show_visual_disjunct:
                color_map = cm.get_cmap("tab10")
                machines = list(self._disjunctive_edges.keys())
                n_colors = len(machines)

                for i, machine in enumerate(machines):
                    if timer.elapsed_time() > time_limit:
                        raise TimeoutError(
                            "time exceeded in creating the visual disjunctive edges"
                        )

                    color = color_map(i / max(n_colors - 1, 1))
                    arcs = self._disjunctive_edges[machine]
                    rad = 0.2 + (i % 3) * 0.1
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
                            arrowsize=15,
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

            suffix: str
            if show_real_disjunct:
                suffix = "real disjunctives"
            elif show_visual_disjunct:
                suffix = "visual disjunctives"
            else:
                suffix = "only conjuntives"
            plt.title(f"{title} - {suffix}")
            plt.axis("off")
            plt.tight_layout()

            if timer.elapsed_time() > time_limit:
                raise TimeoutError("time exceeded in final layout")

            plt.savefig(output_path / f"{title} - {suffix}.png")
            plt.close()
        except TimeoutError as e:
            plt.close()

            print(f"\n[WARNING]: {str(e)}.")
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
        machines_assignment: list[list[int]] = [],
        tech_disjunc: bool = False,
        graph_type: str,
    ):
        if graph_type not in ["fjssp instance", "partial fjssp", "complete fjssp"]:
            print("the FJSSPGraph type must be specified")
            return None

        self._instance = instance

        if graph_type == "fjssp instance":
            self._machines_assignment = [
                set(ops) for ops in self._instance.O_m.values()
            ]
            self._machines_scheduling = self._machines_assignment.copy()

        elif graph_type == "partial fjssp":
            self._machines_assignment = [
                set(assignment) for assignment in machines_assignment
            ]
            self._machines_scheduling = self._machines_assignment.copy()

        elif graph_type == "complete fjssp":
            self._machines_assignment = [
                set(assignment) for assignment in machines_assignment
            ]
            self._machines_scheduling = machines_assignment

        self._dag = DAG(instance)

        if graph_type in ["partial fjssp", "complete fjssp"]:
            ops_machine = {
                op: m
                for op in self._instance.O
                for m, ops in enumerate(self._machines_assignment)
                if op in ops
            }
            for u, v in self._dag._graph.edges:
                if u != "S":
                    self._dag.set_edge_weight(
                        from_node=u,
                        to_node=v,
                        weight=self._instance.p[(u, ops_machine[u])],
                    )

        self._create_disjunctives(tech_disjunc=tech_disjunc, graph_type=graph_type)

    def _create_disjunctives(self, *, tech_disjunc: bool = True, graph_type: str):
        if graph_type == "complete fjssp":
            for machine, sequence in enumerate(self._machines_scheduling):
                for i in range(len(sequence) - 1):
                    from_op = sequence[i]
                    to_op = sequence[i + 1]
                    if tech_disjunc or (
                        self._instance.job_of_op[from_op]
                        != self._instance.job_of_op[to_op]
                    ):
                        self._dag.add_disjunctive_edge(
                            machine,
                            from_op,
                            to_op,
                            weight=self._instance.p[(from_op, machine)],
                            consolidated=True,
                        )

        if graph_type in ["fjssp instance", "partial fjssp"]:
            for machine, ops in enumerate(self._machines_assignment):
                for op1, op2 in combinations(ops, 2):
                    if tech_disjunc or (
                        self._instance.job_of_op[op1] != self._instance.job_of_op[op2]
                    ):
                        self._dag.add_disjunctive_edge(
                            machine,
                            op1,
                            op2,
                            consolidated=False,
                        )

    """
    def _set_edge_weights(self):
        def _are_operations_assigned() -> bool:
            # verifying if each operation is assigned to one single machine
            all_ops = [
                op for machine_seq in self._machines_assignment for op in machine_seq
            ]
            return len(all_ops) == len(set(all_ops))

        instance = self._instance
        for u, v in self._dag._graph.edges:
            if _are_operations_assigned():
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
    """

    def _are_sequence_consolidated(self, machine_id: int) -> bool:
        if not self._machines_scheduling[machine_id]:
            return False

        scheduling = self._machines_scheduling[machine_id]

        for i in range(len(scheduling) - 1):
            from_op = list(scheduling)[i]
            to_op = list(scheduling)[i + 1]
            if (from_op, to_op) not in self._dag._graph.edges:
                return False

        return True

    def consolidate_sequence_on_machine(self, machine_id: int, sequence: list[int]):
        self._machines_scheduling[machine_id] = sequence
        self._machines_assignment[machine_id] = set(sequence)

        for i in range(len(sequence) - 1):
            from_op = sequence[i]
            to_op = sequence[i + 1]
            if self._instance.job_of_op[from_op] != self._instance.job_of_op[to_op]:
                self._dag.add_disjunctive_edge(
                    machine=machine_id,
                    from_node=from_op,
                    to_node=to_op,
                    weight=self._instance.p[(from_op, machine_id)],
                    consolidated=True,
                )

    def remove_sequence_on_machine(self, *, machine_id: int) -> None:
        if self._machines_scheduling[machine_id]:
            sequence = self._machines_scheduling[machine_id]
            for i in range(len(sequence) - 1):
                from_op = list(sequence)[i]
                to_op = list(sequence)[i + 1]
                if self._instance.job_of_op[from_op] != self._instance.job_of_op[to_op]:
                    self._dag._graph.remove_edge(
                        from_op,
                        to_op,
                    )
        self._machines_scheduling[machine_id] = list()

    def longest_path_to(self, op: int) -> float:
        subgraph = self._dag._graph.subgraph(nx.ancestors(self._dag._graph, op) | {op})
        return nx.dag_longest_path_length(subgraph, weight="weight")

    def longest_path_from(self, op: int) -> float:
        subgraph = self._dag._graph.subgraph(
            nx.descendants(self._dag._graph, op) | {op}
        )
        return nx.dag_longest_path_length(subgraph, weight="weight")

    def export_visualization(
        self,
        output_path: Path,
        title: str,
        arrowstyle: str = "->",
        show: str = "visual disjunctives",
        time_limit: float = 30.0,
    ):
        if show not in [
            "visual disjunctives",
            "both",
            "no disjunctives",
            "real disjunctives",
        ]:
            show = "visual disjunctives"

        if show in ["no disjunctives", "both"]:
            self._dag.draw(
                output_path=output_path,
                title=title,
                show_visual_disjunct=False,
                show_real_disjunct=False,
                arrowstyle=arrowstyle,
                time_limit=time_limit,
            )
        if show in ["visual disjunctives", "both"]:
            self._dag.draw(
                output_path=output_path,
                title=title,
                show_visual_disjunct=True,
                show_real_disjunct=False,
                arrowstyle=arrowstyle,
                time_limit=time_limit,
            )
        if show in ["real disjunctives"]:
            self._dag.draw(
                output_path=output_path,
                title=title,
                show_visual_disjunct=False,
                show_real_disjunct=True,
                arrowstyle=arrowstyle,
                time_limit=time_limit,
            )
