import enum
from smtplib import SMTP
import datetime

from mpi4py import MPI

class Status(enum.Enum):
    READY = 0
    DONE = 1
    START = 2
    EXIT = 3

class Worker:

    def __init__(self, work_function):
        self.comm = MPI.COMM_WORLD   # get MPI communicator object
        self.status = MPI.Status()   # get MPI status object
        self.name = MPI.Get_processor_name()
        self.rank = self.comm.rank
        self.function = work_function
        print("I am a worker with rank %d on %s." % (self.rank, self.name))


    def work_loop(self):
        while True:
            self.comm.send(None, dest=0, tag=Status.READY.value)
            task = self.comm.recv(source=0, tag=MPI.ANY_TAG, status=self.status)
            tag = self.status.Get_tag()

            if tag == Status.START.value:

                result = self.function(task)
                self.comm.send(result, dest=0, tag=Status.DONE.value)
            elif tag == Status.EXIT.value:
                break

        self.comm.send(None, dest=0, tag=Status.EXIT.value)


class TaskMaster:
    def __init__(self, task_list, email_creds=None):
        self.comm = MPI.COMM_WORLD   # get MPI communicator object
        self.status = MPI.Status()   # get MPI status object
        self.name = MPI.Get_processor_name()
        self.rank = self.comm.rank
        self.size = self.comm.size
        self.task_list = task_list
        self.email_creds=email_creds

    def do_work(self):
        task_index = 0
        num_workers = self.size - 1
        closed_workers = 0
        print("Master starting with %d workers" % num_workers)
        while closed_workers < num_workers:
            data = self.comm.recv(source=MPI.ANY_SOURCE, tag=MPI.ANY_TAG, status=self.status)
            source = self.status.Get_source()
            tag = self.status.Get_tag()
            if tag == Status.READY.value:
                # Worker is ready, so send it a task
                if task_index < len(self.task_list):
                    self.comm.send(self.task_list[task_index], dest=source, tag=Status.START.value)
                    print("Sending task %d of %d to worker %d" % (task_index, len(self.task_list), source))
                    task_index += 1
                else:
                    self.comm.send(None, dest=source, tag=Status.EXIT.value)
            elif tag == Status.DONE.value:
                print("Got data {} from worker {}".format(data, source))
            elif tag == Status.EXIT.value:
                print("Worker %d exited." % source)
                closed_workers += 1

        print("Master finishing")
        if self.email_creds is not None:
            debuglevel = 0

            smtp = SMTP()
            smtp.set_debuglevel(debuglevel)
            smtp.connect(self.email_creds["smtp"], self.email_creds["port"])
            smtp.starttls()
            smtp.login(self.email_creds["login"], self.email_creds["password"])

            from_addr = self.email_creds["from_address"]
            to_addr = self.email_creds["to_address"]

            subj = "Cluster Calculation Done"
            date = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")

            message_text = "MPI TaskMaster on {} has finished all {} tasks.\n".format(self.name, len(self.task_list))

            msg = "From: %s\nTo: %s\nSubject: %s\nDate: %s\n\n%s" % (from_addr, to_addr, subj, date, message_text)

            smtp.sendmail(from_addr, to_addr, msg)
            smtp.quit()