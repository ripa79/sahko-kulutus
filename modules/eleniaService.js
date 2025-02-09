const axios = require('axios');
const fs = require('fs').promises;
const path = require('path');
const dotenv = require('dotenv');

dotenv.config();

class EleniaService {
    constructor() {
        this.username = process.env.ELENIA_USERNAME;
        this.password = process.env.ELENIA_PASSWORD;
        this.baseUrl = 'https://public.sgp-prod.aws.elenia.fi/api/gen';
        this.cognitoUrl = 'https://cognito-idp.eu-west-1.amazonaws.com/';
        this.headers = {
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'https://ainalab.aws.elenia.fi/',
            'Origin': 'https://ainalab.aws.elenia.fi',
            'Connection': 'keep-alive'
        };
    }

    async getCognitoToken() {
        const payload = {
            AuthFlow: 'USER_PASSWORD_AUTH',
            ClientId: 'k4s2pnm04536t1bm72bdatqct',
            AuthParameters: {
                USERNAME: this.username,
                PASSWORD: this.password
            },
            ClientMetadata: {}
        };

        try {
            const response = await axios.post(this.cognitoUrl, payload, {
                headers: {
                    'Content-Type': 'application/x-amz-json-1.1',
                    'X-Amz-Target': 'AWSCognitoIdentityProviderService.InitiateAuth'
                }
            });

            return response.data.AuthenticationResult.AccessToken;
        } catch (error) {
            console.error('Failed to get Cognito token:', error.message);
            throw error;
        }
    }

    async getCustomerData(bearerToken) {
        const url = `${this.baseUrl}/customer_data_and_token`;
        try {
            const response = await axios.get(url, {
                headers: { ...this.headers, Authorization: `Bearer ${bearerToken}` }
            });

            const metadata = response.data;
            const apiToken = metadata.token;
            const customerId = Object.keys(metadata.customer_datas)[0];
            const customerData = metadata.customer_datas[customerId];

            let consumptionGsrn = null;
            let productionGsrn = null;

            for (const meteringpoint of customerData.meteringpoints) {
                if (meteringpoint.additional_information === 'Liittymällä tuotannon käyttöpaikka.') {
                    consumptionGsrn = meteringpoint.gsrn;
                }
                if (meteringpoint.device?.name === 'Tuotannon virtuaalilaite') {
                    productionGsrn = meteringpoint.gsrn;
                }
            }

            return {
                apiToken,
                customerId,
                consumptionGsrn,
                productionGsrn
            };
        } catch (error) {
            console.error('Failed to get customer data:', error.message);
            throw error;
        }
    }

    async getMeterReadings(apiToken, gsrn, customerId, year, dataType) {
        const url = `${this.baseUrl}/meter_reading_yh`;
        try {
            const response = await axios.get(url, {
                params: {
                    gsrn,
                    customer_ids: customerId,
                    year
                },
                headers: { ...this.headers, Authorization: `Bearer ${apiToken}` }
            });

            // Save the data to a file
            const downloadsDir = path.join(process.cwd(), 'downloads');
            await fs.mkdir(downloadsDir, { recursive: true });
            await fs.writeFile(
                path.join(downloadsDir, `${dataType}_data.json`),
                JSON.stringify(response.data, null, 2)
            );

            return response.data;
        } catch (error) {
            console.error(`Failed to get ${dataType} data:`, error.message);
            throw error;
        }
    }

    async fetchConsumptionData() {
        try {
            const bearerToken = await this.getCognitoToken();
            const { apiToken, customerId, consumptionGsrn, productionGsrn } = await this.getCustomerData(bearerToken);
            const year = process.env.YEAR;

            const promises = [];
            if (consumptionGsrn) {
                promises.push(this.getMeterReadings(apiToken, consumptionGsrn, customerId, year, 'consumption'));
            }
            if (productionGsrn) {
                promises.push(this.getMeterReadings(apiToken, productionGsrn, customerId, year, 'production'));
            }

            await Promise.all(promises);
            console.log('Successfully fetched and saved Elenia data');
        } catch (error) {
            console.error('Error in fetchConsumptionData:', error.message);
            throw error;
        }
    }
}

module.exports = new EleniaService();