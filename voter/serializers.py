from rest_framework import serializers

from voter.models import FileTracker, NCVoter, NCVHis


class FileTrackerSerializer(serializers.ModelSerializer):

    class Meta:
        model = FileTracker
        fields = ('created', 'data_file_kind', 'change_tracker_processed',
                  'updates_processed',)


class NCVHisSerializer(serializers.ModelSerializer):

    class Meta:
        model = NCVHis
        fields = ('county_id', 'ncid', 'voter_reg_num', 'county_desc',
                  'election_desc', 'voting_method', 'voted_party_cd',
                  'pct_description', 'voted_county_desc', 'vtd_label',
                  'vtd_description',)


class NCVoterSerializer(serializers.ModelSerializer):

    class Meta:
        model = NCVoter
        fields = ('ncid', 'county_id', 'birth_age', 'confidential_ind', 'birth_state',
                  'age', 'county_desc', 'voter_reg_num', 'status_cd', 'voter_status_desc',
                  'reason_cd', 'voter_status_reason_desc', 'absent_ind', 'name_prefx_cd',
                  'last_name', 'middle_name', 'first_name',
                  'midl_name', 'name_sufx_cd', 'res_street_address', 'res_city_desc',
                  'state_cd', 'zip_code', 'mail_addr1',
                  'mail_addr2', 'mail_addr3', 'mail_addr4', 'mail_city',
                  'mail_state', 'mail_zipcode', 'full_phone_number', 'race_code',
                  'ethnic_code', 'party_cd', 'gender_code', 'birth_place',
                  'drivers_lic', 'registr_dt', 'precinct_abbrv', 'precinct_desc',
                  'municipality_abbrv', 'municipality_desc', 'ward_abbrv', 'ward_desc',
                  'cong_dist_abbrv', 'super_court_abbrv', 'judic_dist_abbrv', 'nc_senate_abbrv',
                  'nc_house_abbrv', 'county_commiss_abbrv', 'county_commiss_desc', 'township_abbrv',
                  'township_desc', 'school_dist_abbrv', 'school_dist_desc', 'fire_dist_abbrv',
                  'fire_dist_desc', 'water_dist_abbrv', 'water_dist_desc', 'sewer_dist_abbrv',
                  'sewer_dist_desc', 'sanit_dist_abbrv', 'sanit_dist_desc', 'rescue_dist_abbrv',
                  'rescue_dist_desc', 'munic_dist_abbrv', 'munic_dist_desc', 'dist_1_abbrv',
                  'dist_1_desc', 'dist_2_abbrv', 'dist_2_desc', 'vtd_abbrv', 'vtd_desc',)
