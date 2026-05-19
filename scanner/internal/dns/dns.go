package dns

import (
	"net"
)

type Result struct {
	ARecords     []string `json:"a_records"`
	MXRecords    []string `json:"mx_records"`
	TXTRecords   []string `json:"txt_records"`
	DMARCRecords []string `json:"dmarc_records"`
	HasMX        bool     `json:"has_mx"`
	HasSPF       bool     `json:"has_spf"`
	HasDMARC     bool     `json:"has_dmarc"`
	Errors       []string `json:"errors"`
}

func Lookup(domain string) Result {
	result := Result{}

	// A records
	aRecords, err := net.LookupHost(domain)
	if err != nil {
		if dnsErr, ok := err.(*net.DNSError); ok && dnsErr.IsNotFound {
			// No tiene A record directo, puede usar CNAME, no es un error grave
		} else {
			result.Errors = append(result.Errors, "A lookup failed: "+err.Error())
		}
	} else {
		result.ARecords = aRecords
	}

	// MX records
	mxRecords, err := net.LookupMX(domain)
	if err != nil {
		if dnsErr, ok := err.(*net.DNSError); ok && dnsErr.IsNotFound {
			// No tiene MX, penalizado via has_mx = false
		} else {
			result.Errors = append(result.Errors, "MX lookup failed: "+err.Error())
		}
	} else {
		for _, mx := range mxRecords {
			if mx.Host != "." {
				result.MXRecords = append(result.MXRecords, mx.Host)
			}
		}
		result.HasMX = len(result.MXRecords) > 0
	}

	// TXT records
	txtRecords, err := net.LookupTXT(domain)
	if err != nil {
		if dnsErr, ok := err.(*net.DNSError); ok && dnsErr.IsNotFound {
			// No tiene TXT records
		} else {
			result.Errors = append(result.Errors, "TXT lookup failed: "+err.Error())
		}
	} else {
		result.TXTRecords = txtRecords
		for _, txt := range txtRecords {
			if len(txt) > 6 && txt[:6] == "v=spf1" {
				result.HasSPF = true
			}
		}
	}

	// DMARC
	dmarcRecords, err := net.LookupTXT("_dmarc." + domain)
	if err == nil {
		for _, txt := range dmarcRecords {
			if len(txt) > 8 && txt[:8] == "v=DMARC1" {
				result.HasDMARC = true
				result.DMARCRecords = append(result.DMARCRecords, txt)
			}
		}
	}

	return result
}