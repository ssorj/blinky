_Errors(self, "/errors.html")

class _Errors(_brbn.Resource):
    def process(self, request):
        url = request.require("url")

        response = _requests.get(url)
        request.proxied_content = response.text

    def render(self, request):
        pass

_lines_before = 5
_lines_after = 20

_error_expr = _re.compile(r"(^|\s|\*)(error|fail|failed|failure|timeout)s?($|\s|:)", _re.IGNORECASE)

def _find_error_windows(lines):
    matching_lines = list()

    for index, line in enumerate(lines):
        if _re.search(_error_expr, line):
            matching_lines.append(index)

    # Filter out known false positives

    filtered_lines = list()

    for index in matching_lines:
        line = lines[index]

        if "Failures: 0, Errors: 0" in line:
            continue

        if "-- Performing Test" in line:
            continue

        if "timeout=" in line:
            continue

        if "Test timeout computed to be" in line:
            continue

        filtered_lines.append(index)

    # Compute windows

    windows = list()

    for index in filtered_lines:
        start = max(0, index - _lines_before)
        end = min(len(lines), index + _lines_after)

        windows.append((start, end))

    # Collapse overlapping windows

    collapsed_windows = list()
    collapsed_window = None

    for window in windows:
        if collapsed_window is None:
            collapsed_window = window

        if window[0] < collapsed_window[1]:
            collapsed_window = collapsed_window[0], window[1]
        else:
            collapsed_windows.append(collapsed_window)
            collapsed_window = window

    if collapsed_window is not None:
        collapsed_windows.append(collapsed_window)

    # for window in windows:
    #     print("w", window)

    # for window in collapsed_windows:
    #     print("c", window)

    return collapsed_windows
