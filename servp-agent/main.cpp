#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <getopt.h>
#include <signal.h>
#include <sys/wait.h>
#include <sys/socket.h>
#include <arpa/inet.h>
#include <string>
#include <vector>
using namespace std;

#include "common.h"
#include "transferdata.h"

void compile_info()
{
	printf("compile time: %s %s\n", __DATE__, __TIME__);
	printf("platform: %s\n", __VERSION__);
}

void usage()
{
	printf("usage:  -d daemon\n"
			"        -s src ip\n"
			"        -p src port\n"
			"        -t target ip\n"
			"        -c target port\n");
}

static vector<pid_t> g_s_pidSet;

void sig_chld(int signo)
{
	pid_t pid;
	int stat;
	while ((pid = waitpid(-1, &stat, WNOHANG)) > 0){
		printf("child %d terminated\n", pid);
	}
}

void setsig()
{
	signal(SIGCHLD, sig_chld); 
}

int work(bool bdaemon, serv_map* pservm)
{
	if (bdaemon){
		printf("start run[daemon] ...");
		daemon(1, 1);
	}
	else{
		printf("start run ...");
	}
	// begin listen
	struct sockaddr_in lsn_addr;
	bzero(&lsn_addr, sizeof(lsn_addr));
	int sock_lsn_fd = socket(AF_INET, SOCK_STREAM, 0);
	lsn_addr.sin_family = AF_INET;
	if (pservm->m_sip.length() == 0)
		lsn_addr.sin_addr.s_addr = INADDR_ANY;
	else{
		inet_pton(AF_INET, pservm->m_sip.c_str(), &lsn_addr.sin_addr.s_addr);
	}
	lsn_addr.sin_port = htons(pservm->m_usrc_port);
	if (bind(sock_lsn_fd, (struct sockaddr*)&lsn_addr, sizeof(struct sockaddr))<0){
		perror("bind error");
		return -1;
	}
	if (listen(sock_lsn_fd, 20) < 0){
		perror("listen error");
		return -1;
	}
	printf("listen port: %d\n", pservm->m_usrc_port);

	int client_fd;
	for ( ; ; ){
		struct sockaddr_in remote_addr;
		socklen_t nsocksize = sizeof(struct sockaddr_in);
		client_fd=accept(sock_lsn_fd, (struct sockaddr*)&remote_addr, &nsocksize);
		if (client_fd < 0){
			perror("accept error");
			continue;
		}
		int child_pid = fork();
		if (child_pid == 0){
			printf("create child process: %d\n", getpid());
			transserver otserver(32, 32);
			if (otserver.transferdata(client_fd, pservm) < 0)
				return -1;
			return 0;
		}
		else if (child_pid > 0){
			// g_s_pidSet.push_back(child_pid);
		}
		else {
			perror("create child proc fail");
		}
		close(client_fd);
	}
	return 0;
}

int main(int argc, char* argv[])
{
	if (argc == 1){
		usage();
		return EXIT_SUCCESS;
	}
	serv_map oserv_map;
	bool bdaemon = false;
	unsigned int uport=0;
	int c = 0;
	while ((c = getopt(argc, argv, "dvs:p:t:c:")) != -1){
		switch(c){
			case 'd':
				bdaemon = true;
				break;
			case 'v':
				compile_info();
				return EXIT_SUCCESS;
				break;
			case 's':
				oserv_map.m_sip = optarg;
				break;
			case 'p':
				oserv_map.m_usrc_port = atoi(optarg);
				break;
			case 't':
				oserv_map.m_tip = optarg;
				break;
			case 'c':
				oserv_map.m_utarget_port = atoi(optarg);
				break;
			default:
				usage();
				return EXIT_SUCCESS;
		}
	}
	setsig();
	if (work(bdaemon, &oserv_map) <0){
		return EXIT_FAILURE;
	}
	return EXIT_SUCCESS;
}
