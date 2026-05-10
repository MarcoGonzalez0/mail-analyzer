package dns

import (
	"net"
)

// Define estructura Result para almacenar los resultados de la consulta DNS
type Result struct {
	ARecords  []string `json:"a_records"`
	MXRecords []string `json:"mx_records"`
	TXTRecords []string `json:"txt_records"`
	HasMX     bool     `json:"has_mx"`
	HasSPF    bool     `json:"has_spf"`
	HasDMARC  bool     `json:"has_dmarc"`
	Errors    []string `json:"errors"`
}

func Lookup(domain string) Result {
	result := Result{}

	// A records
	aRecords, err := net.LookupHost(domain)
	if err != nil {
		result.Errors = append(result.Errors, "A lookup failed: "+err.Error())
	} else {
		result.ARecords = aRecords
	}

	// MX records
	mxRecords, err := net.LookupMX(domain)
	if err != nil {
		result.Errors = append(result.Errors, "MX lookup failed: "+err.Error())
	} else {
		for _, mx := range mxRecords {
			result.MXRecords = append(result.MXRecords, mx.Host)
		}
		result.HasMX = len(result.MXRecords) > 0
	}

	// TXT records (SPF y DMARC viven aquí)
	txtRecords, err := net.LookupTXT(domain)
	if err != nil {
		result.Errors = append(result.Errors, "TXT lookup failed: "+err.Error())
	} else {
		result.TXTRecords = txtRecords
		for _, txt := range txtRecords {
			if len(txt) > 6 && txt[:6] == "v=spf1" {
				result.HasSPF = true
			}
		}
	}

	// DMARC vive en un subdominio especial
	dmarcRecords, err := net.LookupTXT("_dmarc." + domain)
	if err == nil {
		for _, txt := range dmarcRecords {
			if len(txt) > 8 && txt[:8] == "v=DMARC1" {
				result.HasDMARC = true
			}
		}
	}

	return result
}