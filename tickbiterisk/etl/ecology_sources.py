from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


ECOLOGY_RAW_DIR = Path("data/raw/ecology")

USGS_ANNUAL_NLCD_ACCESS_URL = (
    "https://www.usgs.gov/centers/eros/science/annual-nlcd-data-access"
)
USGS_ANNUAL_NLCD_OVERVIEW_URL = "https://www.usgs.gov/annualNLCD"
MRLC_DATA_SERVICES_URL = "https://www.mrlc.gov/data-services-page"
CENSUS_BPS_PAGE_URL = "https://www.census.gov/construction/bps/index.html"
CENSUS_BPS_COUNTY_INDEX_URL = "https://www2.census.gov/econ/bps/County/"
CENSUS_BPS_DOCUMENTATION_URL = "https://www2.census.gov/econ/bps/Documentation/"
USDA_MARYLAND_CDL_URL = (
    "https://data.nass.usda.gov/Statistics_by_State/Maryland/"
    "Publications/Cropland_Data_Layer/index.php"
)
USDA_CROPSCAPE_URL = "https://www.nass.usda.gov/Research_and_Science/Cropland/Viewer/"
MARYLAND_DNR_GAME_MAMMALS_URL = (
    "https://dnr.maryland.gov/wildlife/Pages/hunt_trap/GameMammals.aspx"
)
EPA_ENVIROATLAS_DATA_DOWNLOAD_URL = "https://www.epa.gov/enviroatlas/data-download"
USDA_FIA_EVALIDATOR_URL = (
    "https://research.fs.usda.gov/products/dataandtools/evalidator-and-fiadb-api"
)
USDA_FIA_API_DOCS_URL = "https://apps.fs.usda.gov/fiadb-api"
MARYLAND_DNR_ARCHERY_HUNTER_SURVEY_URL = (
    "https://dnr.maryland.gov/wildlife/pages/hunt_trap/bhsurvey.aspx"
)
MARYLAND_DNR_BOWHUNTER_SURVEY_REPORT_URL = (
    "https://dnr.maryland.gov/wildlife/Documents/BowHunterSurveyReport.pdf"
)


@dataclass(frozen=True)
class EcologySourceFile:
    source_id: str
    family: str
    url: str
    raw_relative_path: str
    description: str
    expected_format: str
    citation_url: str = ""
    acquisition_procedure: str = ""
    access_notes: str = ""
    parser_method: str = "not_run_raw_acquisition_only"
    extraction_quality: str = "not_evaluated_at_raw_acquisition"
    modeling_caveats: str = "not_model_input_until_parser_and_backtest_acceptance"

    def raw_path(self, raw_dir: Path = ECOLOGY_RAW_DIR) -> Path:
        return raw_dir / self.raw_relative_path

    @property
    def resolved_citation_url(self) -> str:
        return self.citation_url or self.url

    @property
    def resolved_acquisition_procedure(self) -> str:
        return (
            self.acquisition_procedure
            or "Fetch the registered official source URL with "
            "`tickbiterisk etl ecology-sources` and keep raw bytes under "
            "ignored raw storage for parser/audit review."
        )

    @property
    def resolved_access_notes(self) -> str:
        return (
            self.access_notes
            or "Public web source; no API key or secret is embedded in the "
            "registry. Respect upstream terms and rate limits."
        )


@dataclass(frozen=True)
class MarylandDnrMastReportSource:
    year: int
    url: str

    @property
    def source_id(self) -> str:
        return f"maryland_dnr_wmd_mast_survey_{self.year}"

    @property
    def raw_relative_path(self) -> str:
        return f"mast/maryland_dnr_wmd_mast_survey_{self.year}.pdf"

    def as_source_file(self) -> EcologySourceFile:
        return EcologySourceFile(
            source_id=self.source_id,
            family="mast",
            url=self.url,
            raw_relative_path=self.raw_relative_path,
            description=f"Maryland DNR Western Maryland mast survey summary {self.year}",
            expected_format="pdf",
        )


MARYLAND_DNR_MAST_REPORT_URLS = [
    MarylandDnrMastReportSource(
        year=2017,
        url="https://dnr.maryland.gov/wildlife/Documents/WMD_Mast_Survey.pdf",
    ),
    MarylandDnrMastReportSource(
        year=2020,
        url="https://dnr.maryland.gov/wildlife/documents/2020_wmd_mastsurvey_summary.pdf",
    ),
    MarylandDnrMastReportSource(
        year=2021,
        url="https://dnr.maryland.gov/wildlife/Documents/2021_WMD_MastSurvey_Summary.pdf",
    ),
]


ECOLOGY_SOURCE_FILES = [
    EcologySourceFile(
        source_id="usgs_annual_nlcd_access",
        family="habitat",
        url=USGS_ANNUAL_NLCD_ACCESS_URL,
        raw_relative_path="nlcd/usgs_annual_nlcd_access.html",
        description="USGS Annual NLCD data access page",
        expected_format="html",
    ),
    EcologySourceFile(
        source_id="usgs_annual_nlcd_overview",
        family="habitat",
        url=USGS_ANNUAL_NLCD_OVERVIEW_URL,
        raw_relative_path="nlcd/usgs_annual_nlcd_overview.html",
        description="USGS Annual NLCD overview page",
        expected_format="html",
    ),
    EcologySourceFile(
        source_id="mrlc_data_services",
        family="habitat",
        url=MRLC_DATA_SERVICES_URL,
        raw_relative_path="nlcd/mrlc_data_services.html",
        description="MRLC data services page for Annual NLCD services",
        expected_format="html",
    ),
    EcologySourceFile(
        source_id="census_bps_page",
        family="construction",
        url=CENSUS_BPS_PAGE_URL,
        raw_relative_path="building_permits/census_bps_page.html",
        description="Census Building Permits Survey landing page",
        expected_format="html",
    ),
    EcologySourceFile(
        source_id="census_bps_county_index",
        family="construction",
        url=CENSUS_BPS_COUNTY_INDEX_URL,
        raw_relative_path="building_permits/census_bps_county_index.html",
        description="Census BPS county ASCII file index",
        expected_format="html",
    ),
    EcologySourceFile(
        source_id="census_bps_documentation",
        family="construction",
        url=CENSUS_BPS_DOCUMENTATION_URL,
        raw_relative_path="building_permits/census_bps_documentation_index.html",
        description="Census BPS documentation index",
        expected_format="html",
    ),
    EcologySourceFile(
        source_id="usda_nass_maryland_cdl",
        family="agriculture",
        url=USDA_MARYLAND_CDL_URL,
        raw_relative_path="cdl/usda_nass_maryland_cdl.html",
        description="USDA NASS Maryland Cropland Data Layer page",
        expected_format="html",
    ),
    EcologySourceFile(
        source_id="usda_nass_cropscape",
        family="agriculture",
        url=USDA_CROPSCAPE_URL,
        raw_relative_path="cdl/usda_nass_cropscape.html",
        description="USDA NASS CropScape viewer page",
        expected_format="html",
    ),
    EcologySourceFile(
        source_id="maryland_dnr_game_mammals_mast_link",
        family="mast",
        url=MARYLAND_DNR_GAME_MAMMALS_URL,
        raw_relative_path="mast/maryland_dnr_game_mammals.html",
        description="Maryland DNR Game Mammals page linking mast survey reports",
        expected_format="html",
    ),
    EcologySourceFile(
        source_id="epa_enviroatlas_data_download",
        family="habitat",
        url=EPA_ENVIROATLAS_DATA_DOWNLOAD_URL,
        raw_relative_path="enviroatlas/epa_enviroatlas_data_download.html",
        description="EPA EnviroAtlas national data download page with county CSV batch tables",
        expected_format="html",
    ),
    EcologySourceFile(
        source_id="usda_fia_evalidator",
        family="forest_inventory",
        url=USDA_FIA_EVALIDATOR_URL,
        raw_relative_path="forest_inventory/usda_fia_evalidator.html",
        description="USDA Forest Service FIA EVALIDator and FIADB API landing page",
        expected_format="html",
    ),
    EcologySourceFile(
        source_id="usda_fia_api_docs",
        family="forest_inventory",
        url=USDA_FIA_API_DOCS_URL,
        raw_relative_path="forest_inventory/usda_fia_api_docs.html",
        description="USDA Forest Service FIADB API documentation",
        expected_format="html",
    ),
    EcologySourceFile(
        source_id="maryland_dnr_archery_hunter_survey",
        family="wildlife_observation",
        url=MARYLAND_DNR_ARCHERY_HUNTER_SURVEY_URL,
        raw_relative_path="wildlife_observation/maryland_dnr_archery_hunter_survey.html",
        description="Maryland DNR Archery Hunter Survey page for wildlife observations",
        expected_format="html",
    ),
    EcologySourceFile(
        source_id="maryland_dnr_bowhunter_survey_report",
        family="wildlife_observation",
        url=MARYLAND_DNR_BOWHUNTER_SURVEY_REPORT_URL,
        raw_relative_path="wildlife_observation/maryland_dnr_bowhunter_survey_report.pdf",
        description="Maryland DNR Bowhunter Survey report PDF",
        expected_format="pdf",
    ),
    *[source.as_source_file() for source in MARYLAND_DNR_MAST_REPORT_URLS],
]
