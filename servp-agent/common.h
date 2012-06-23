/*
 * =====================================================================================
 *
 *       Filename:  common.h
 *
 *    Description:  
 *
 *        Version:  1.0
 *        Created:  2012年03月28日 14时41分30秒
 *       Revision:  none
 *       Compiler:  gcc
 *
 * =====================================================================================
 */

#ifndef __common_h__
#define __common_h__

#include <string>
using namespace std;

typedef struct _serv_map
{
	_serv_map():m_usrc_port(0),m_utarget_port(0)
	{ }
	string m_sip;
	unsigned int m_usrc_port;
	string m_tip;
	unsigned int m_utarget_port;
} serv_map;

#endif //__common_h__
