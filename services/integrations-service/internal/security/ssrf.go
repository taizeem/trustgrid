package security

import (
	"fmt"
	"net"
	"net/url"
	"strings"

	"github.com/trustgrid/integrations-service/internal/domain"
)

var privateCIDRs []*net.IPNet

func init() {
	cidrs := []string{
		"0.0.0.0/8",       // RFC 1122 "this" network (routes to localhost on Linux)
		"10.0.0.0/8",      // RFC 1918 private
		"100.64.0.0/10",   // RFC 6598 Carrier-Grade NAT (Shared Address Space)
		"127.0.0.0/8",     // IPv4 loopback
		"169.254.0.0/16",  // RFC 3927 Link-local / Cloud Metadata (169.254.169.254)
		"172.16.0.0/12",   // RFC 1918 private
		"192.0.0.0/24",    // RFC 6890 IETF Protocol Assignments
		"192.0.2.0/24",    // RFC 5737 Documentation (TEST-NET-1)
		"192.168.0.0/16",  // RFC 1918 private
		"198.18.0.0/15",   // RFC 2544 Network Interconnect Benchmark Testing
		"198.51.100.0/24", // RFC 5737 Documentation (TEST-NET-2)
		"203.0.113.0/24",  // RFC 5737 Documentation (TEST-NET-3)
		"224.0.0.0/4",     // RFC 5771 Multicast
		"240.0.0.0/4",     // RFC 1112 Reserved / Future Use
		"::/128",          // IPv6 unspecified
		"::1/128",         // IPv6 loopback
		"fc00::/7",        // RFC 4193 Unique local address (ULA)
		"fe80::/10",       // RFC 4291 Link-local unicast
		"ff00::/8",        // RFC 4291 Multicast
	}

	for _, c := range cidrs {
		_, block, err := net.ParseCIDR(c)
		if err == nil {
			privateCIDRs = append(privateCIDRs, block)
		}
	}
}

type SSRFValidator struct {
	AllowPrivate bool
}

func NewSSRFValidator(allowPrivate bool) *SSRFValidator {
	return &SSRFValidator{AllowPrivate: allowPrivate}
}

// isRestrictedIP checks if an IP is in any private, loopback, or reserved range.
func isRestrictedIP(ip net.IP) bool {
	if ip.IsLoopback() || ip.IsPrivate() || ip.IsUnspecified() || ip.IsLinkLocalUnicast() || ip.IsLinkLocalMulticast() || ip.IsInterfaceLocalMulticast() {
		return true
	}

	for _, block := range privateCIDRs {
		if block.Contains(ip) {
			return true
		}
	}

	return false
}

func (v *SSRFValidator) ValidateURL(rawURL string) error {
	parsed, err := url.ParseRequestURI(rawURL)
	if err != nil {
		return fmt.Errorf("%w: %v", domain.ErrInvalidURL, err)
	}

	scheme := strings.ToLower(parsed.Scheme)
	if scheme != "http" && scheme != "https" {
		return fmt.Errorf("%w: scheme must be http or https", domain.ErrInvalidURL)
	}

	host := parsed.Hostname()
	if host == "" {
		return fmt.Errorf("%w: missing host", domain.ErrInvalidURL)
	}

	if v.AllowPrivate {
		return nil
	}

	lowerHost := strings.ToLower(host)
	if lowerHost == "localhost" || strings.HasSuffix(lowerHost, ".localhost") || strings.HasSuffix(lowerHost, ".local") || strings.HasSuffix(lowerHost, ".internal") {
		return fmt.Errorf("%w: target %s is a restricted local or internal domain", domain.ErrSSRFBlocked, host)
	}

	// If host is an IP literal, validate immediately without DNS lookup
	if parsedIP := net.ParseIP(host); parsedIP != nil {
		if isRestrictedIP(parsedIP) {
			return fmt.Errorf("%w: target %s is a restricted IP address", domain.ErrSSRFBlocked, host)
		}
		return nil
	}

	// Resolve hostnames to prevent DNS rebinding or spoofed internal targets
	ips, err := net.LookupIP(host)
	if err != nil {
		return fmt.Errorf("%w: host resolution failed: %v", domain.ErrInvalidURL, err)
	}

	if len(ips) == 0 {
		return fmt.Errorf("%w: host resolved to zero IP addresses", domain.ErrInvalidURL)
	}

	for _, ip := range ips {
		if isRestrictedIP(ip) {
			return fmt.Errorf("%w: target %s resolves to restricted IP %s", domain.ErrSSRFBlocked, host, ip.String())
		}
	}

	return nil
}
