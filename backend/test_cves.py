from app.services.cve_data import ALL_CVES

print(f"Total CVEs: {len(ALL_CVES)}")
vendors = set(c["vendor"] for c in ALL_CVES)
print(f"Vendors: {vendors}")
for vendor in sorted(vendors):
    count = len([c for c in ALL_CVES if c["vendor"] == vendor])
    print(f"  {vendor}: {count} CVEs")
