/* qnx-porter: glibc <endian.h> names, from QNX's <net/netbyte.h> */
#include <net/netbyte.h>
#ifndef be16toh
#define be16toh(x) __NET_BE16((x))
#endif
#ifndef be32toh
#define be32toh(x) __NET_BE32((x))
#endif
#ifndef be64toh
#define be64toh(x) __NET_BE64((x))
#endif
#ifndef betoh16
#define betoh16(x) __NET_BE16((x))
#endif
#ifndef betoh32
#define betoh32(x) __NET_BE32((x))
#endif
#ifndef betoh64
#define betoh64(x) __NET_BE64((x))
#endif
#ifndef htobe16
#define htobe16(x) __NET_BE16((x))
#endif
#ifndef htobe32
#define htobe32(x) __NET_BE32((x))
#endif
#ifndef htobe64
#define htobe64(x) __NET_BE64((x))
#endif
#ifndef htole16
#define htole16(x) __NET_LE16((x))
#endif
#ifndef htole32
#define htole32(x) __NET_LE32((x))
#endif
#ifndef htole64
#define htole64(x) __NET_LE64((x))
#endif
#ifndef le16toh
#define le16toh(x) __NET_LE16((x))
#endif
#ifndef le32toh
#define le32toh(x) __NET_LE32((x))
#endif
#ifndef le64toh
#define le64toh(x) __NET_LE64((x))
#endif
#ifndef letoh16
#define letoh16(x) __NET_LE16((x))
#endif
#ifndef letoh32
#define letoh32(x) __NET_LE32((x))
#endif
#ifndef letoh64
#define letoh64(x) __NET_LE64((x))
#endif
