## TODO

* Do we really need the complicated `llen`, `brpop` in a pipeline, sleep, etc, for 
retrieving the results? Why can't we just `brpop`. I did that originally because it seemed
spamming single `brpop`s was noticeably slowing down rate, but I am starting to doubt that now.

* Throw an error if the function/args the user is trying to serialize ends up being larger
than X MB, for some reasonable X. Do we also want to do this from the worker?
