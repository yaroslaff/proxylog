# ProxyLog
Reverse HTTP (GET/HEAD) proxy with logging (todo)


## Example apache config
<VirtualHost *:80>
	DocumentRoot /var/www/PROXY/
	ServerName PROXY
	ErrorLog /var/log/apache2/error.log
	CustomLog /var/log/apache2/proxy_access.log combined_time
	Options -Indexes +FollowSymLinks


	<Directory /var/www/PROXY>
		Options -Indexes +FollowSymLinks
	</Directory>

    RewriteEngine On
    RewriteCond %{HTTPS} !=on
    RewriteCond %{REQUEST_URI} !^/\.well\-known        
    RewriteRule (.*) https://%{SERVER_NAME}$1 [R=301,L]

</VirtualHost>

<VirtualHost *:443>
        DocumentRoot /var/www/PROXY/
        ServerName PROXY
        ErrorLog /var/log/apache2/error.log
        CustomLog /var/log/apache2/proxy_access.log combined
        Options -Indexes +FollowSymLinks


        <Directory /var/www/PROXY>
                Options -Indexes +FollowSymLinks
        </Directory>

    SSLEngine on
    # SSLCertificateFile /etc/letsencrypt/live/PROXY/fullchain.pem
    # SSLCertificateKeyFile /etc/letsencrypt/live/PROXY/privkey.pem
    SSLCertificateFile /var/lib/dehydrated/certs/PROXY/fullchain.pem
    SSLCertificateKeyFile /var/lib/dehydrated/certs/PROXY/privkey.pem

    Header always set Strict-Transport-Security "max-age=31536000; includeSubDomains"


    <Location /php/>
        ProxyPreserveHost On
        ProxyPass http://127.0.0.1:8080/
        ProxyPassReverse http://127.0.0.1:8080/
    </Location>

    ProxyPreserveHost Off
    ProxyPass / https://PROXY_TARGET/
    ProxyPassReverse / https://PROXY_TARGET/

</VirtualHost>
