import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.cm as cm

from pathlib import Path


def plot_gantt(
    *,
    start_times: dict[int, float],
    machine_assignments: dict[int, int],
    processing_times: dict[tuple[int, int], float],
    job_of_op: dict[int, int],
    machine_set: list[int],
    title: str = "Gantt Chart",
    show_labels: bool = True,
    figsize=(12, 6),
    verbose: bool = True,
    output_file_path: Path,
) -> None:
    _, ax = plt.subplots(figsize=figsize)

    jobs = sorted(set(job_of_op.values()))
    job_colors = {job: cm.tab20(job % 20) for job in jobs}

    yticks = []
    yticklabels = []

    bar_height = 0.6
    spacing = 1.5

    latest_end = 0

    for m_idx, m in enumerate(sorted(machine_set)):
        y = m_idx * spacing
        yticks.append(y)
        yticklabels.append(f"machine {m}")

        ops_on_m = [i for i, m_i in machine_assignments.items() if m_i == m]
        for i in ops_on_m:
            s = start_times[i]
            p = processing_times[(i, m)]
            job = job_of_op[i]
            color = job_colors[job]

            ax.barh(
                y=y,
                width=p,
                left=s,
                height=bar_height,
                color=color,
                edgecolor="black",
                alpha=0.9,
            )

            if show_labels:
                ax.text(
                    s + p / 2,
                    y,
                    f"Op {i}",
                    ha="center",
                    va="center",
                    fontsize=8,
                    color="white",
                )

            latest_end = max(latest_end, s + p)

    ax.set_yticks(yticks)
    ax.set_yticklabels(yticklabels)
    ax.set_xlabel("time")
    ax.set_title(title)
    ax.grid(True, axis="x", linestyle="--", alpha=0.5)

    ax.axvline(
        latest_end,
        color="darkred",
        linestyle="--",
        linewidth=2,
        label=f"makespan = {latest_end:.1f}",
    )
    ax.text(
        latest_end,
        ax.get_ylim()[1] + 0.2,
        f"{latest_end:.1f}",
        color="darkred",
        ha="center",
        fontsize=10,
        fontweight="bold",
    )

    legend_handles = [
        mpatches.Patch(color=color, label=f"Job {job}")
        for job, color in job_colors.items()
    ]
    ax.legend(
        handles=legend_handles, title="jobs", bbox_to_anchor=(1.05, 1), loc="upper left"
    )

    plt.tight_layout()

    plt.savefig(output_file_path)

    if verbose:
        plt.show()
