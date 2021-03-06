from wok.task import Task

task = Task()

sum = 0

@task.main()
def main():
	log = task.logger()

	values, result = task.ports("x", "sum")

	count = 0
	sum = 0
	for v in values:
		count += 1
		sum += v

	log.info("Sum of {0} numbers = {1}".format(count, sum))
	
	result.send(sum)

task.start()
