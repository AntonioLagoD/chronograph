from datetime import datetime

import sys

__author__ = 'Anubhav Jain <ajain@lbl.gov>'

"""
A Chronograph implementation used to time execution of code. Features include:
    - multiple verbosity levels
    - built-in logging
    - JSON output
    - custom exception handling
    - manage global list of named chronographs
    - function decorators

Not intended for extremely precise timing (e.g., sub-millisecond level).
"""

all_chronographs = {}  # global list of chronographs


def get_chronograph(name, **kwargs):
    """
    Get a chronograph and save it the global list of chronographs
    :param name: (str) the name of this chronograph
    :param kwargs: (**kwargs) parameters to feed into the Chronograph constructor
    :return: a Chronograph object
    """
    if name not in all_chronographs:
        all_chronographs[name] = Chronograph(name, **kwargs)

    return all_chronographs[name]


def add_chronograph(**kwargs1):
    """
    A function decorator for timing things. Each execution of the function will be timed,
    and the total will be stored in the global Chronograph.
    :param kwargs: (**kwargs) parameters to feed into the Chronograph constructor
    :return: (this is a function decorator)
    """

    def _add_chronograph_internal(func):
        def _decorator(*args, **kwargs):
            my_name = func.__name__
            my_chronograph = get_chronograph(my_name, **kwargs1)
            my_chronograph.start()
            return_data = func(*args, **kwargs)
            my_chronograph.stop()
            return return_data
        return _decorator
    return _add_chronograph_internal


class Chronograph():

    def __init__(self, name=None, verbosity=0, m_logger=None, log_lvl=None, start_timing=False, throw_exceptions=False):
        """
        A class to represent a Chronograph for timing code execution
        :param name: (str) a name, useful when reporting or saving global Chronographs
        :param verbosity: (int) set to 0=silent operation, 2=most verbose operation
        :param m_logger: (Logger) logging object for writing output. Defaults to sys.stdout
        :param log_lvl: (str) level to log at, e.g. "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"
        :param start_timing: (bool) set to True if you want to start timing immediately by calling start() function
        :param throw_exceptions: (bool) set to True if you want invalid Chronograph commands to result in exceptions
        """
        self.name = name
        self.header = "Chronograph {}".format(name) if name else "Chronograph"
        self.timing_data = []
        self.verbosity = verbosity
        self.throw_exceptions = throw_exceptions

        if m_logger:
            self.print_fnc = getattr(m_logger, log_lvl.lower())
        else:
            self.print_fnc = sys.stdout.write

        if start_timing:
            self.start()

    def start(self, label=None):
        """
        Starts timing a new split.
        :param label: (str) a label to apply to this split (useful for reporting)
        """
        if not self.timing_data or "stop" in self.timing_data[-1]:
            label = label if label else str(len(self.timing_data)+1)
            self.timing_data.append({"start": datetime.now(), "label": label})
            if self.verbosity >= 2:
                self.print_fnc("{}: Split ({}) started at: {}\n".format(self.header, label, self.timing_data[-1]["start"]))
            return True
        else:
            msg = "{}: Warning: Cannot start Chronograph while in current state! Stop or reset chronograph before starting.\n".format(self.header)
            if self.throw_exceptions:
                raise ValueError(msg)
            self.print_fnc(msg)
            return False

    def stop(self):
        """
        Stops timing.
        """
        if self.timing_data and "stop" not in self.timing_data[-1]:
            self.timing_data[-1]["stop"] = datetime.now()
            if self.verbosity >= 2:
                self.print_fnc("{}: stopped at: {}\n".format(self.header, self.timing_data[-1]["start"]))
            if self.verbosity >= 1:
                last_split = self.last_split
                last_split_text = "Last split ({}) time: {} s.".format(last_split['label'], get_split_time(last_split))

                self.print_fnc("{}: Total elapsed time: {} s. {}\n".format(self.header, self.total_elapsed_time, last_split_text))
            return True
        else:
            self.print_fnc("{}: Warning: Cannot stop Chronograph while in current state! Start chronograph first.\n".format(self.header))
            return False

    def reset(self):
        """
        Resets and clears all timing data.
        """
        self.timing_data = []
        if self.verbosity >= 2:
            self.print_fnc("{}: Reset at: {}\n".format(self.header, self.timing_data[-1]["start"]))
            return True
        return False

    def split(self, label=None):
        """
        Stops the current split and immediately starts a new split, perhaps with a new label.
        :param label: (str) a label to apply to this split (useful for reporting)
        :return: (bool) if the split was created successfully (used internally)
        """
        success = self.stop()
        if success:
            success = self.start(label=label)
        return success

    @property
    def total_elapsed_time(self):
        """
        The total elapsed time (all splits) for the Chronograph
        :return: (float)
        """
        elapsed_time = 0.0
        for t in self.timing_data:
            start_time = t['start']
            stop_time = t['stop'] if 'stop' in t else datetime.now()
            elapsed_time += (stop_time - start_time).total_seconds()

        return elapsed_time

    @property
    def last_split(self):
        """
        The complete timing data of the last completed split.
        :return: (dict)
        """
        for t in reversed(self.timing_data):
            if 'stop' in t:
                return t
        return False

    @property
    def last_split_time(self):
        """
        The time elapsed for the last completed split.
        :return: (float)
        """
        return get_split_time(self.last_split) if self.last_split else 0

    @property
    def timing_data(self):
        """
        All timing data.
        :return: (JSON array of dicts)
        """
        return self.timing_data

    def report(self):
        """
        Prints a full report of timing data as a string.
        """
        report_str = "Report for {}\n".format(self.header)
        for t in self.timing_data:
            split_time = get_split_time(t, True)
            running_text = "" if "stop" in t else " (still running)"
            report_str += "Split {}: {}{}\n".format(t["label"], split_time, running_text)

        report_str += "Total elapsed time: {}\n".format(self.total_elapsed_time)

        self.print_fnc(report_str)

    def __float__(self):
        return self.total_elapsed_time

    def __str__(self):
        return "{} with total elapsed time: {}".format(self.header, self.total_elapsed_time)

    def __repr__(self):
        return "{} with total elapsed time: {} and timing data: {}".format(self.header, self.total_elapsed_time, self.timing_data)

    def __enter__(self):
        self.start()

    def __exit__(self, type, value, tb):
        self.stop()


def get_split_time(split_data, allow_still_running=False):
    if "stop" in split_data:
        stop_time = split_data["stop"]
    elif allow_still_running:
        stop_time = datetime.now()
    else:
        raise ValueError("Cannot get split data; make sure 'stop' is defined or use 'allow_still_running' option.")

    return (stop_time - split_data['start']).total_seconds()


@add_chronograph()
def time_me():
    import time
    time.sleep(3)

if __name__ == "__main__":

    x = time_me()
    print get_chronograph("time_me")
    """
    c = Chronograph()
    c.start()
    print("Hello")
    c.stop()
    print(float(c))
    print(str(c))
    print(repr(c))
    """


    """
    print("dasf")
    with get_chronograph("hello") as f:
        import time
        time.sleep(3)

    print get_chronograph("hello").total_elapsed_time
    """

    """
    c = get_chronograph("global", verbosity=1)
    print c.verbosity

    c = get_chronograph("global")
    print c.verbosity
    """

    """
    x = Chronograph(name="my stopwatch", verbosity=1)
    x.start("part 1")
    x.stop()
    x.start("part 2")
    x.split()
    x.split("part 4")
    import time
    time.sleep(3)
    x.stop()
    x.report()
    """

# TODO: add examples

# TODO: add unit tests (based on examples)