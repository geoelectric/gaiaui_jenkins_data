This is a set of tools to crunch Mozilla Gaia UI Jenkins results.

`pull_jenkins_html.py` pulls down html results incrementally from the jenkins server. A `config.ini` is required as follows:

    [Jenkins]
    server = ...
    user = ...
    password = ...

If a particular job name is given, it will pull results for that job. Otherwise, it pulls from a preset list of jobs relevant to Gaia UI testing.

`crunch_jenkins_html.py` iterates over the given job and outputs a summary table of results.

`sample-job\` and `sample-results.txt` are included. The former will let you try out the crunching script, and the latter is an example of the output.

