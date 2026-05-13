# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Legacy-template → archetype-config mapping.

Each of the 28 pre-existing scenario templates routes through the
new architecture generator. This file is the single source of truth
for that mapping; updating it doesn't require touching the legacy
template Python files (they continue to ship their freeform device /
flow definitions as historical metadata, but the actual scenario
materialization comes from the generator).

Templates not in the mapping fall back to the legacy freeform path.
The `testing/duplicate_mac_demo` template is intentionally excluded
because its purpose (intentional duplicate MACs) is incompatible with
the realism rules the generator enforces.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.services.architecture.archetypes._base import (
    ScaleTier,
    VendorProfile,
)


@dataclass(frozen=True)
class TemplateArchetypeConfig:
    """Maps a legacy template ID to an archetype + scale + vendor."""

    archetype_id: str
    vendor_profile: VendorProfile
    scale: ScaleTier
    overrides: dict[str, Any] | None = None


# `(vertical, template_name)` -> archetype config.
LEGACY_TEMPLATE_ARCHETYPES: dict[
    tuple[str, str], TemplateArchetypeConfig,
] = {
    # ------------------------------------------------------------------
    # MANUFACTURING (4)
    # ------------------------------------------------------------------
    ("manufacturing", "siemens_discrete_manufacturing"):
        TemplateArchetypeConfig(
            archetype_id="manufacturing_discrete_cell",
            vendor_profile=VendorProfile.SIEMENS_SHOP,
            scale=ScaleTier.MEDIUM,
            overrides={"zone_themes": {
                "cell1": "Discrete_Machining",
                "cell2": "Assembly",
                "cell3": "Quality_Inspection",
            }},
        ),
    ("manufacturing", "rockwell_automotive_assembly"):
        TemplateArchetypeConfig(
            archetype_id="manufacturing_discrete_cell",
            vendor_profile=VendorProfile.ROCKWELL_SHOP,
            scale=ScaleTier.MEDIUM,
            overrides={"zone_themes": {
                "cell1": "Body_Welding",
                "cell2": "Paint_Booth",
                "cell3": "Final_Trim",
            }},
        ),
    ("manufacturing", "multi_vendor_enterprise_manufacturing"):
        TemplateArchetypeConfig(
            archetype_id="manufacturing_discrete_cell",
            vendor_profile=VendorProfile.MULTI_VENDOR,
            scale=ScaleTier.LARGE,
            overrides={"zone_themes": {
                "cell1": "Stamping",
                "cell2": "Body_Shop",
                "cell3": "Paint",
                "cell4": "Final_Assembly",
            }},
        ),
    ("manufacturing", "strict_purdue_segmented"):
        TemplateArchetypeConfig(
            archetype_id="manufacturing_discrete_cell",
            vendor_profile=VendorProfile.MULTI_VENDOR,
            scale=ScaleTier.MEDIUM,
            overrides={"zone_themes": {
                "cell1": "CNC_Machining",
                "cell2": "Robotic_Welding",
                "cell3": "ECoat_Treatment",
            }},
        ),
    # Phase 10 showcase templates.
    ("manufacturing", "semiconductor_fab_300mm"):
        TemplateArchetypeConfig(
            archetype_id="manufacturing_semiconductor_fab",
            vendor_profile=VendorProfile.MULTI_VENDOR,
            scale=ScaleTier.MEDIUM,
            # Bay names already meaningful in the archetype, no overrides.
        ),
    ("manufacturing", "ev_battery_cell_plant"):
        TemplateArchetypeConfig(
            archetype_id="manufacturing_battery_cell",
            vendor_profile=VendorProfile.MULTI_VENDOR,
            scale=ScaleTier.MEDIUM,
        ),
    ("manufacturing", "pharma_vaccine_bioreactor"):
        TemplateArchetypeConfig(
            archetype_id="manufacturing_pharma_bioreactor",
            vendor_profile=VendorProfile.DCS_EMERSON,
            scale=ScaleTier.MEDIUM,
        ),

    # ------------------------------------------------------------------
    # WATER (4) — all map to master/remote SCADA
    # ------------------------------------------------------------------
    ("water_wastewater", "small_utility_scada"):
        TemplateArchetypeConfig(
            archetype_id="water_utility_master_remote",
            vendor_profile=VendorProfile.MIXED_FIELD,
            scale=ScaleTier.SMALL,
            overrides={"zone_themes": {
                "station1": "Lift_Station_North",
                "station2": "Lift_Station_South",
                "station3": "Booster_Station",
            }},
        ),
    ("water_wastewater", "municipal_water_treatment"):
        TemplateArchetypeConfig(
            archetype_id="water_utility_master_remote",
            vendor_profile=VendorProfile.MIXED_FIELD,
            scale=ScaleTier.MEDIUM,
            overrides={"zone_themes": {
                "station1": "Intake_Headworks",
                "station2": "Coagulation",
                "station3": "Filtration",
                "station4": "Disinfection",
                "station5": "Distribution_Pumping",
            }},
        ),
    ("water_wastewater", "regional_pump_station_network"):
        TemplateArchetypeConfig(
            archetype_id="water_utility_master_remote",
            vendor_profile=VendorProfile.MIXED_FIELD,
            scale=ScaleTier.LARGE,
            overrides={"zone_themes": {
                "station1": "High_Capacity_Pump_1",
                "station2": "High_Capacity_Pump_2",
                "station3": "Medium_Pump_North",
                "station4": "Medium_Pump_South",
                "station5": "Medium_Pump_East",
                "station6": "Booster_Station_1",
                "station7": "Booster_Station_2",
                "station8": "Storage_Tank_Site",
            }},
        ),
    ("water_wastewater", "wastewater_treatment_facility"):
        TemplateArchetypeConfig(
            archetype_id="water_utility_master_remote",
            vendor_profile=VendorProfile.MIXED_FIELD,
            scale=ScaleTier.LARGE,
            overrides={"zone_themes": {
                "station1": "Headworks_Screening",
                "station2": "Primary_Clarifier",
                "station3": "Aeration_Basin",
                "station4": "Secondary_Clarifier",
                "station5": "Disinfection_UV",
                "station6": "Sludge_Thickening",
                "station7": "Anaerobic_Digester",
                "station8": "Effluent_Pumping",
            }},
        ),

    # ------------------------------------------------------------------
    # ENERGY (4) — substation + generation
    # ------------------------------------------------------------------
    ("energy_power", "electrical_substation"):
        TemplateArchetypeConfig(
            archetype_id="energy_substation",
            vendor_profile=VendorProfile.SEL_PROTECTION,
            scale=ScaleTier.MEDIUM,
            overrides={"zone_themes": {
                "bay1": "Feeder_Bay",
                "bay2": "Bus_Bay",
                "bay3": "Transformer_Bay",
            }},
        ),
    ("energy_power", "grid_control_center"):
        TemplateArchetypeConfig(
            archetype_id="energy_substation",
            vendor_profile=VendorProfile.SEL_PROTECTION,
            scale=ScaleTier.MULTI_SITE,
            overrides={"zone_themes": {
                "bay1": "Feeder_Protection",
                "bay2": "Bus_Protection",
                "bay3": "Transformer_Protection",
                "bay4": "Line_Protection",
                "bay5": "Capacitor_Bank",
                "bay6": "Reactor_Bank",
            }},
        ),
    ("energy_power", "gas_turbine_generation"):
        TemplateArchetypeConfig(
            archetype_id="energy_generation_combined_cycle",
            vendor_profile=VendorProfile.DCS_EMERSON,
            scale=ScaleTier.MEDIUM,
            overrides={"zone_themes": {
                "unit1": "Gas_Turbine_1",
                "unit2": "Gas_Turbine_2",
                "unit3": "Steam_Turbine",
            }},
        ),
    ("energy_power", "solar_bess_microgrid"):
        TemplateArchetypeConfig(
            archetype_id="energy_substation",
            vendor_profile=VendorProfile.MIXED_FIELD,
            scale=ScaleTier.MEDIUM,
            overrides={"zone_themes": {
                "bay1": "Inverter_String_Array",
                "bay2": "BESS_Rack",
                "bay3": "Point_of_Interconnection",
            }},
        ),

    # ------------------------------------------------------------------
    # OIL & GAS (4)
    # ------------------------------------------------------------------
    ("oil_gas", "emerson_offshore_platform"):
        TemplateArchetypeConfig(
            archetype_id="oil_gas_refinery",
            vendor_profile=VendorProfile.DCS_EMERSON,
            scale=ScaleTier.MEDIUM,
            overrides={"zone_themes": {
                "unit1": "Wellhead_Control",
                "unit2": "Separation_Train",
                "unit3": "Gas_Compression",
            }},
        ),
    ("oil_gas", "honeywell_lng_terminal"):
        TemplateArchetypeConfig(
            archetype_id="oil_gas_refinery",
            vendor_profile=VendorProfile.DCS_HONEYWELL,
            scale=ScaleTier.LARGE,
            overrides={"zone_themes": {
                "unit1": "Liquefaction_Train",
                "unit2": "Cryogenic_Storage",
                "unit3": "Boil_Off_Recovery",
                "unit4": "Loading_Terminal",
            }},
        ),
    ("oil_gas", "yokogawa_refinery_unit"):
        TemplateArchetypeConfig(
            archetype_id="oil_gas_refinery",
            vendor_profile=VendorProfile.DCS_YOKOGAWA,
            scale=ScaleTier.MEDIUM,
            overrides={"zone_themes": {
                "unit1": "Crude_Distillation",
                "unit2": "Hydrocracker",
                "unit3": "Reformer",
            }},
        ),
    ("oil_gas", "pipeline_scada_network"):
        TemplateArchetypeConfig(
            archetype_id="water_utility_master_remote",
            vendor_profile=VendorProfile.MIXED_FIELD,
            scale=ScaleTier.LARGE,
            overrides={"zone_themes": {
                "station1": "Compressor_Station_1",
                "station2": "Compressor_Station_2",
                "station3": "Pump_Station_3",
                "station4": "Custody_Transfer_Meter",
                "station5": "Block_Valve_Site_5",
                "station6": "Block_Valve_Site_6",
                "station7": "Tank_Farm",
                "station8": "Receipt_Terminal",
            }},
        ),

    # ------------------------------------------------------------------
    # BUILDING AUTOMATION (3)
    # ------------------------------------------------------------------
    ("building_automation", "commercial_office_bms"):
        TemplateArchetypeConfig(
            archetype_id="building_automation_bas_supervisor",
            vendor_profile=VendorProfile.BAS_TRIDIUM,
            scale=ScaleTier.MEDIUM,
            overrides={"zone_themes": {
                "zone1": "Lobby_HVAC",
                "zone2": "Floor_2_East",
                "zone3": "Floor_2_West",
            }},
        ),
    ("building_automation", "university_campus_bms"):
        TemplateArchetypeConfig(
            archetype_id="building_automation_bas_supervisor",
            vendor_profile=VendorProfile.BAS_TRIDIUM,
            scale=ScaleTier.LARGE,
            overrides={"zone_themes": {
                "zone1": "Library_Building",
                "zone2": "Science_Building",
                "zone3": "Student_Center",
                "zone4": "Athletic_Complex",
            }},
        ),
    ("building_automation", "data_center_infrastructure"):
        TemplateArchetypeConfig(
            archetype_id="data_center_infra_dcim",
            vendor_profile=VendorProfile.DCIM_CISCO,
            scale=ScaleTier.MEDIUM,
            overrides={"zone_themes": {
                "rack1": "Compute_Row_A",
                "rack2": "Compute_Row_B",
                "rack3": "Storage_Row",
                "rack4": "Network_Row",
            }},
        ),

    # ------------------------------------------------------------------
    # DISTRIBUTION / LOGISTICS (4)
    # ------------------------------------------------------------------
    ("distribution_logistics", "cold_chain_warehouse"):
        TemplateArchetypeConfig(
            archetype_id="distribution_warehouse",
            vendor_profile=VendorProfile.ROCKWELL_SHOP,
            scale=ScaleTier.MEDIUM,
            overrides={"zone_themes": {
                "zone1": "Frozen_Storage",
                "zone2": "Chilled_Storage",
                "zone3": "Ambient_Loading",
            }},
        ),
    ("distribution_logistics", "distribution_center"):
        TemplateArchetypeConfig(
            archetype_id="distribution_warehouse",
            vendor_profile=VendorProfile.ROCKWELL_SHOP,
            scale=ScaleTier.LARGE,
            overrides={"zone_themes": {
                "zone1": "Receiving",
                "zone2": "Putaway",
                "zone3": "Pick_Pack",
                "zone4": "Shipping",
            }},
        ),
    ("distribution_logistics", "fulfillment_center"):
        TemplateArchetypeConfig(
            archetype_id="distribution_warehouse",
            vendor_profile=VendorProfile.ROCKWELL_SHOP,
            scale=ScaleTier.LARGE,
            overrides={"zone_themes": {
                "zone1": "Pick_Module",
                "zone2": "Pack_Stations",
                "zone3": "Shipping_Sortation",
                "zone4": "Returns_Processing",
            }},
        ),
    ("distribution_logistics", "parcel_sorting_hub"):
        TemplateArchetypeConfig(
            archetype_id="distribution_warehouse",
            vendor_profile=VendorProfile.MULTI_VENDOR,
            scale=ScaleTier.MEDIUM,
            overrides={"zone_themes": {
                "zone1": "Inbound_Sortation",
                "zone2": "Cross_Belt_Sorter",
                "zone3": "Outbound_Loading",
            }},
        ),

    # ------------------------------------------------------------------
    # TRANSPORTATION (4)
    # ------------------------------------------------------------------
    ("transportation", "highway_corridor_its"):
        TemplateArchetypeConfig(
            archetype_id="transportation_atms_corridor",
            vendor_profile=VendorProfile.ATMS_NTCIP,
            scale=ScaleTier.LARGE,
            overrides={"zone_themes": {
                "intersection1": "Mile_1_Interchange",
                "intersection2": "Mile_3_Ramp",
                "intersection3": "Mile_5_DMS",
                "intersection4": "Mile_7_Interchange",
                "intersection5": "Mile_9_Ramp",
                "intersection6": "Mile_11_DMS",
                "intersection7": "Mile_13_Interchange",
                "intersection8": "Mile_15_Ramp",
                "intersection9": "Mile_17_RWIS",
                "intersection10": "Mile_19_DMS",
            }},
        ),
    ("transportation", "toll_plaza_operations"):
        TemplateArchetypeConfig(
            archetype_id="transportation_toll_plaza",
            vendor_profile=VendorProfile.ATMS_NTCIP,
            scale=ScaleTier.MEDIUM,
            overrides={"zone_themes": {
                "lane1": "Lane_1_ETC",
                "lane2": "Lane_2_ETC",
                "lane3": "Lane_3_Manual",
                "lane4": "Lane_4_Manual",
            }},
        ),
    ("transportation", "tunnel_control_system"):
        TemplateArchetypeConfig(
            archetype_id="transportation_tunnel",
            vendor_profile=VendorProfile.ATMS_NTCIP,
            scale=ScaleTier.MEDIUM,
            overrides={"zone_themes": {
                "tunnel_section1": "Tunnel_North_Bore",
                "tunnel_section2": "Tunnel_Mid_Bore",
                "tunnel_section3": "Tunnel_South_Bore",
            }},
        ),
    ("transportation", "urban_intersection_network"):
        TemplateArchetypeConfig(
            archetype_id="transportation_atms_corridor",
            vendor_profile=VendorProfile.ATMS_NTCIP,
            scale=ScaleTier.LARGE,
            overrides={"zone_themes": {
                "intersection1": "Main_at_1st",
                "intersection2": "Main_at_2nd",
                "intersection3": "Main_at_3rd",
                "intersection4": "Broad_at_1st",
                "intersection5": "Broad_at_2nd",
                "intersection6": "Broad_at_3rd",
                "intersection7": "Park_at_1st",
                "intersection8": "Park_at_2nd",
                "intersection9": "River_Bridge",
                "intersection10": "Highway_Onramp",
            }},
        ),

    # ------------------------------------------------------------------
    # TESTING — intentionally NOT in the mapping. The duplicate-MAC
    # demo's authoring intent is incompatible with the generator's
    # realism guarantees.
    # ------------------------------------------------------------------
}


def get_archetype_config(
    vertical: str, template_name: str,
) -> TemplateArchetypeConfig | None:
    """Look up the archetype config for a legacy template.

    Returns None if the template isn't on the archetype rail (falls
    back to the legacy freeform definition path).
    """
    return LEGACY_TEMPLATE_ARCHETYPES.get((vertical, template_name))
