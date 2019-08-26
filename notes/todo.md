## TODO

* Do we really need the complicated `llen`, `brpop` in a pipeline, sleep, etc, for 
retrieving the results? Why can't we just `brpop`. I did that originally because it seemed
spamming single `brpop`s was noticeably slowing down rate, but I am starting to doubt that now.

* Throw an error if the function/args the user is trying to serialize ends up being larger
than X MB, for some reasonable X. Do we also want to do this from the worker?

* Concept of a task id (multiple `remote_map`s shouldn't interfere with each other, especially when
they are called non-blocking)

* Optimization (chunk ordering, worker selection) shouldn't be inside `Manager`

* Unit tests/benchmarks with a local redis instance and local workers at least

* Dummy redis instance for unit tests (since we'll just use localhost)

* Make `worker.py` into a class since it's getting too fragmented

* `requirements.txt` or pip-able

* redis url (and maybe other things) in a `config.py` file

* Instead of `return_metadata` returning a list of pairs (result,metadata dict), just have it
return a dict where the result is a key in the metadata dict, and no need for pairs
