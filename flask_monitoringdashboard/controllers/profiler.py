from collections import defaultdict

import numpy, os

from flask_monitoringdashboard.core.profiler.util import PathHash
from flask_monitoringdashboard.core.timezone import to_local_datetime
from flask_monitoringdashboard.database import row2dict
from flask_monitoringdashboard.database.stack_line import (
    get_profiled_requests,
    get_grouped_profiled_requests,
)


def get_profiler_table(session, endpoint_id, offset, per_page):
    """
    :param session: session for the database
    :param endpoint_id: endpoint to filter on
    :param offset: number of items that are skipped
    :param per_page: number of items that are returned (at most)
    """
    table = get_profiled_requests(session, endpoint_id, offset, per_page)

    for idx, row in enumerate(table):
        row.time_requested = to_local_datetime(row.time_requested)
        table[idx] = row2dict(row)
        stack_lines = []
        for line in row.stack_lines:
            obj = row2dict(line)
            obj['code'] = row2dict(line.code)
            stack_lines.append(obj)
        table[idx]['stack_lines'] = stack_lines
    return table


def get_lines_changed_since_version(version_1, version_2):
    """
    :param version_1: version/commit id
    :param version_2: version/commit id
    :return: a list of endpoints changed since the version
    """
    command = """
        git show {commit_1}^..{commit_2}    |
        grep -E '^\+'                       |
        sed 's/^\+//'                       |
        grep -v '^\+'                       |
        sed -e 's/^[ ]*//'                  |
        sort                                |
        uniq """
    command_output = os.popen(
        command.format(
            commit_1=version_1,
            commit_2=version_2
            )
        ).read()
    lines_list = command_output.splitlines()
    
    command = """
        git show {commit_1}^..{commit_2}    |
        grep -E 'def '                      |
        grep -v 'import '                   |
        sed 's/@@.*@@//'                    |
        sed 's/def //'                      |
        sed 's/ //'                         |
        sed 's/://'                         |
        sed '/^$/d'                         |
        sort                                |
        uniq """
    command_output = os.popen(
        command.format(
            commit_1=version_1,
            commit_2=version_2
            )
        ).read()
    endpoints_list = command_output.splitlines()

    complete_list = lines_list + endpoints_list
    print(complete_list)
    return complete_list


def get_grouped_profiler(session, endpoint_id, version=None, previous_results=[], changes=[]):
    """
    :param session: session for the database
    :param endpoint_id: endpoint to filter on
    :return:
    """
    requests = get_grouped_profiled_requests(session, endpoint_id, version)
    session.expunge_all()

    histogram = defaultdict(list)  # path -> [list of values]
    path_hash = PathHash()

    for r in requests:
        for index, stack_line in enumerate(r.stack_lines):
            key = path_hash.get_stacklines_path(r.stack_lines, index)
            histogram[key].append(stack_line.duration)

    table = []
    for key, duration_list in sorted(histogram.items(), key=lambda row: row[0]):
        previous = next((x for x in previous_results if x['id'] == key), None)

        hits = len(duration_list)
        duration = sum(duration_list)
        avg_duration = duration / hits
        std = numpy.std(duration_list)
        total_hits = len(requests)

        prev_hits = previous['hits'] if previous is not None else 0
        prev_duration = previous['duration'] if previous is not None else 0
        prev_avg_duration = previous['avg_duration'] if previous is not None else 0

        was_changed = path_hash.get_code(key) in changes
        duration_change = (avg_duration - prev_avg_duration) / prev_avg_duration if prev_avg_duration is not 0 else avg_duration
        regression = bool(was_changed and (avg_duration - prev_avg_duration) > std)

        table.append(
            {
                'id': key,
                'indent': path_hash.get_indent(key) - 1,
                'code': path_hash.get_code(key),
                'hits': hits,
                'duration': duration,
                'avg_duration': avg_duration,
                'std': std,
                'total_hits': total_hits,

                'previous_hits': prev_hits,
                'previous_duration': prev_duration,
                'previous_avg_duration': prev_avg_duration,

                'was_changed': was_changed,
                'duration_change': duration_change,
                'regression': regression,
            }
        )
    return table
