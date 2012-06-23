/*
 * =====================================================================================
 *
 *       Filename:  transferdata.h
 *
 *    Description:  
 *
 *        Version:  1.0
 *        Created:  2012年03月28日 14时29分06秒
 *       Revision:  none
 *       Compiler:  gcc
 *
 * =====================================================================================
 */

#ifndef __transfer_data_h__
#define __transfer_data_h__

#include "common.h"

class transserver{
	public:
		transserver(int nInBufSize, int nOutBufSize);
		virtual ~transserver();

	int transferdata(int sockfd, serv_map* pserv_map);

	protected:
	int connect_serv(const char* ptarget_ip, unsigned int uport);
	void set_nonblock(int fd, bool bblock = true);


	protected:
	int m_remotesockfd;
	int m_targetsockfd;

	unsigned int	m_nInBuffSize;
	unsigned int	m_nOutBuffSize;
	unsigned char*	m_pInBuff;
	unsigned char*	m_pOutBuff;

};

#endif //__transfer_data_h__
