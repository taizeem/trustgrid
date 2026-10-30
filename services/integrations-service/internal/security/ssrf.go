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
		"127.0.0.0/8",    // IPv4 loopback
		"10.0.0.0/8",     // RFC1918 private
		"172.16.0.0/12",  // RFC1918 private
		"192.168.0.0/16", // RFC1918 private
		"169.254.0.0/16", // Link-local / Cloud Metadata
		"::1/128",        // IPv6 loopback
		"fc00::/7",       // Unique local address
		"fe80::/10",      // Link-local IPv6
		"224.0.0.0/4",    // Multicast
		"ff00::/8",       // IPv6 multicast
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

	// Resolve IP addresses to prevent DNS rebinding or hostname spoofing
	ips, err := net.LookupIP(host)
	if err != nil {
		return fmt.Errorf("%w: host resolution failed: %v", domain.ErrInvalidURL, err)
	}

	for _, ip := range ips {
		for _, block := range privateCIDRs {
			if block.Contains(ip) {
				return fmt.Errorf("%w: target %s resolves to restricted IP %s", domain.ErrSSRFBlocked, host, ip.String())
			}
		}
	}

	return nil
}
