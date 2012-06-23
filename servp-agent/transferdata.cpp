/*
 * =====================================================================================
 *
 *       Filename:  transferdata.cpp
 *
 *    Description:  
 *
 *        Version:  1.0
 *        Created:  2012年03月28日 14时44分47秒
 *       Revision:  none
 *       Compiler:  gcc
 *
 * =====================================================================================
 */

#include <unistd.h>
#include <sys/time.h>
#include <sys/socket.h>
#include <arpa/inet.h>
#include <fcntl.h>

#include "transferdata.h"

#define M_SIZE 0x1<<20 

transserver::transserver(int nInBufSize, int nOutBufSize)
	:m_pInBuff(NULL), m_pOutBuff(NULL)
{
	m_nInBuffSize = nInBufSize * M_SIZE;
	m_nOutBuffSize = nOutBufSize * M_SIZE;
	m_pInBuff = new unsigned char[m_nInBuffSize];
	m_pOutBuff = new unsigned char[m_nOutBuffSize];
}

transserver::~transserver()
{
	if (m_pInBuff == NULL){
		delete[] m_pInBuff;
		m_pInBuff = NULL;
	}
	if (m_pOutBuff == NULL){
		delete[] m_pOutBuff;
		m_pOutBuff = NULL;
	}
}

int transserver::transferdata(int sockfd, serv_map* pserv_map)
{
	m_remotesockfd = sockfd;
	m_targetsockfd = connect_serv(pserv_map->m_tip.c_str(), pserv_map->m_utarget_port);
	if (m_targetsockfd < 0)
		return -1;
	printf("targetsockfd %d\n", m_targetsockfd);
	fd_set rset;
	FD_ZERO(&rset);
	FD_SET(m_remotesockfd, &rset);
	FD_SET(m_targetsockfd, &rset);
	struct timeval tv;
	tv.tv_sec = 3;
	tv.tv_usec = 0;

	set_nonblock(m_remotesockfd);
	set_nonblock(m_targetsockfd);

	while (true){
		fd_set tmp_rset = rset;
		struct timeval tmp_tv = tv;
		int retval = select(m_targetsockfd+1, &tmp_rset, NULL, NULL, &tmp_tv);
		if (retval = 0){
			continue;
		}
		if (retval < 0){
			if (errno == EINTR)
				continue;
			perror("select error");
			break;
		}
		if (FD_ISSET(m_remotesockfd, &tmp_rset) != 0){
			int datasize = recv(m_remotesockfd, m_pInBuff, m_nInBuffSize, 0);
			if (datasize > 0){
				send(m_targetsockfd, m_pInBuff, datasize, 0);
			}
			else if (datasize == 0){
				printf("close connect\n");
				break;
			}
		}
		if (FD_ISSET(m_targetsockfd, &tmp_rset) != 0){
			int datasize = recv(m_targetsockfd, m_pOutBuff, m_nOutBuffSize, 0);
			if (datasize > 0){
				send(m_remotesockfd, m_pOutBuff, datasize, 0);
			}
			else if (datasize <= 0){
				perror("out data failure");
				break;
			}
		}
	}
	
	return 0;
}

// method
int transserver::connect_serv(const char* ptarget_ip, unsigned int uport)
{
	struct sockaddr_in socktarget;
	bzero(&socktarget, sizeof(struct sockaddr_in));
	inet_pton(AF_INET, ptarget_ip, &socktarget.sin_addr.s_addr);
	socktarget.sin_family = AF_INET;
	socktarget.sin_port = htons(uport);
	printf("target ip %s\n", ptarget_ip);
	printf("target port %u\n", uport);
	int sockfd = socket(AF_INET, SOCK_STREAM, 0);

	// connect server port
	int retval = connect(sockfd, (struct sockaddr*)&socktarget, sizeof(struct sockaddr_in));
	printf("connect %d success\n", retval);
	if (retval < 0){
		printf("connect target fail: %s\n", ptarget_ip);
		return -1;
	}
	return sockfd;
}

void transserver::set_nonblock(int fd, bool bblock)
{
	int flags = fcntl(fd, F_GETFL, 0);
	if (bblock){
		flags |= O_NONBLOCK;
	}
	else{
		flags |= ~O_NONBLOCK;
	}
	fcntl(fd, F_SETFL, flags);
}
