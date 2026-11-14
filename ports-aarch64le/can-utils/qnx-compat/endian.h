#ifndef _QNX_PORTER_ENDIAN_H
#define _QNX_PORTER_ENDIAN_H

#if defined(__has_include)
#  if __has_include(<net/netbyte.h>)
#    include <net/netbyte.h>
#  endif
#else
#  include <net/netbyte.h>
#endif

/* Byte order constants */
#ifndef __LITTLE_ENDIAN
#  define __LITTLE_ENDIAN 1234
#endif
#ifndef __BIG_ENDIAN
#  define __BIG_ENDIAN 4321
#endif
#ifndef __PDP_ENDIAN
#  define __PDP_ENDIAN 3412
#endif
#ifndef __BYTE_ORDER
#  if defined(__BYTE_ORDER__)
#    define __BYTE_ORDER __BYTE_ORDER__
#  elif defined(__ORDER_LITTLE_ENDIAN__) && defined(__ORDER_BIG_ENDIAN__)
#    if defined(__BIG_ENDIAN__)
#      define __BYTE_ORDER __BIG_ENDIAN
#    else
#      define __BYTE_ORDER __LITTLE_ENDIAN
#    endif
#  else
#    define __BYTE_ORDER __LITTLE_ENDIAN
#  endif
#endif

#ifndef LITTLE_ENDIAN
#  define LITTLE_ENDIAN __LITTLE_ENDIAN
#endif
#ifndef BIG_ENDIAN
#  define BIG_ENDIAN __BIG_ENDIAN
#endif
#ifndef PDP_ENDIAN
#  define PDP_ENDIAN __PDP_ENDIAN
#endif
#ifndef BYTE_ORDER
#  define BYTE_ORDER __BYTE_ORDER
#endif

/* Endian conversion macros */
#ifndef be16toh
#  define be16toh(x) __NET_BE16((x))
#endif
#ifndef be32toh
#  define be32toh(x) __NET_BE32((x))
#endif
#ifndef be64toh
#  define be64toh(x) __NET_BE64((x))
#endif
#ifndef betoh16
#  define betoh16(x) __NET_BE16((x))
#endif
#ifndef betoh32
#  define betoh32(x) __NET_BE32((x))
#endif
#ifndef betoh64
#  define betoh64(x) __NET_BE64((x))
#endif
#ifndef htobe16
#  define htobe16(x) __NET_BE16((x))
#endif
#ifndef htobe32
#  define htobe32(x) __NET_BE32((x))
#endif
#ifndef htobe64
#  define htobe64(x) __NET_BE64((x))
#endif
#ifndef htole16
#  define htole16(x) __NET_LE16((x))
#endif
#ifndef htole32
#  define htole32(x) __NET_LE32((x))
#endif
#ifndef htole64
#  define htole64(x) __NET_LE64((x))
#endif
#ifndef le16toh
#  define le16toh(x) __NET_LE16((x))
#endif
#ifndef le32toh
#  define le32toh(x) __NET_LE32((x))
#endif
#ifndef le64toh
#  define le64toh(x) __NET_LE64((x))
#endif
#ifndef letoh16
#  define letoh16(x) __NET_LE16((x))
#endif
#ifndef letoh32
#  define letoh32(x) __NET_LE32((x))
#endif
#ifndef letoh64
#  define letoh64(x) __NET_LE64((x))
#endif

#endif /* _QNX_PORTER_ENDIAN_H */
