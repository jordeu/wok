from wok.task import Task

task = Task()

@task.generator()
def sequence(value_port):
	conf = task.conf
	start = conf.get("start", 0, dtype=int)
	size = conf.get("size", 100, dtype=int)

	log = task.logger()
	log.info("Generating values from {0} to {1}".format(start, start + size - 1))

	for v in xrange(start, start + size):
		value_port.send(v)

task.start()
	
