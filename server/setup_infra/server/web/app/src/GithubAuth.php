<?php
declare(strict_types=1);
final class GithubAuth {
    public static function configured(): bool {
        return (bool)(getenv('GITHUB_CLIENT_ID')&&getenv('GITHUB_CLIENT_SECRET')&&getenv('GITHUB_REDIRECT_URI'));
    }
    private static function configuration(): array {
        if(!self::configured()){throw new InvalidArgumentException('El ingreso con GitHub está pendiente de configuración. Consultá al administrador.');}
        $uri=getenv('GITHUB_REDIRECT_URI');$parts=parse_url($uri);
        if(!$parts||!in_array($parts['scheme']??'',['http','https'],true)||empty($parts['host'])||isset($parts['user'])||isset($parts['fragment'])){throw new RuntimeException('La URL de retorno de GitHub no es válida.');}
        return ['client_id'=>getenv('GITHUB_CLIENT_ID'),'client_secret'=>getenv('GITHUB_CLIENT_SECRET'),'redirect_uri'=>$uri];
    }
    public static function begin(): string {
        $config=self::configuration();Auth::logout();
        $state=bin2hex(random_bytes(32));$verifier=rtrim(strtr(base64_encode(random_bytes(64)),'+/','-_'),'=');
        $_SESSION['oauth']=['state'=>$state,'verifier'=>$verifier,'started'=>time()];
        return 'https://github.com/login/oauth/authorize?'.http_build_query([
            'client_id'=>$config['client_id'],'redirect_uri'=>$config['redirect_uri'],'scope'=>'read:user user:email',
            'state'=>$state,'code_challenge'=>rtrim(strtr(base64_encode(hash('sha256',$verifier,true)),'+/','-_'),'='),'code_challenge_method'=>'S256'
        ],'','&',PHP_QUERY_RFC3986);
    }
    /** Peticiones servidor a servidor. Nunca seguir redirects ni guardar tokens. */
    private static function fetch(string $url,array $headers,?array $data=null): array {
        $method=$data===null?'GET':'POST';$content=$data===null?'':http_build_query($data,'','&',PHP_QUERY_RFC3986);
        if($data!==null){$headers[]='Content-Type: application/x-www-form-urlencoded';}
        $headers[]='User-Agent: SGLAB-Laboratorios';
        $context=stream_context_create(['http'=>['method'=>$method,'header'=>implode("\r\n",$headers),'content'=>$content,'timeout'=>15,'ignore_errors'=>true,'follow_location'=>0,'max_redirects'=>0], 'ssl'=>['verify_peer'=>true,'verify_peer_name'=>true]]);
        $stream=@fopen($url,'rb',false,$context);
        if(!$stream){throw new RuntimeException('No se pudo conectar con GitHub. Intentá nuevamente.');}
        try{$body=stream_get_contents($stream,1048577);$meta=stream_get_meta_data($stream);}finally{fclose($stream);}
        $status=0;foreach(($meta['wrapper_data']??[]) as $line){if(preg_match('/^HTTP\/\S+ ([0-9]{3})/',$line,$m)){$status=(int)$m[1];}}
        if($status!==200||$body===false||strlen($body)>1048576){throw new RuntimeException('GitHub no pudo completar la verificación. Intentá nuevamente.');}
        try{$result=json_decode($body,true,512,JSON_THROW_ON_ERROR);}catch(JsonException){throw new RuntimeException('GitHub devolvió una respuesta inválida.');}
        if(!is_array($result)){throw new RuntimeException('GitHub devolvió una respuesta inválida.');}return $result;
    }
    public static function callback(array $input,?Closure $fetch=null): void {
        $pending=$_SESSION['oauth']??null;unset($_SESSION['oauth']);
        $state=$input['state']??null;
        if(!$pending||!is_string($state)||!hash_equals($pending['state'],$state)||time()-$pending['started']>600){throw new HttpError(403,'La autorización de GitHub venció o no corresponde a esta sesión. Volvé a iniciar el acceso.');}
        if(isset($input['error'])){throw new InvalidArgumentException('No se autorizó el acceso con GitHub. Podés volver a intentarlo.');}
        $code=$input['code']??null;
        if(!is_string($code)||$code===''||strlen($code)>1024){throw new InvalidArgumentException('GitHub no devolvió un código de autorización válido.');}
        $config=self::configuration();$fetch??=self::fetch(...);
        $response=$fetch('https://github.com/login/oauth/access_token',['Accept: application/json'],[...$config,'code'=>$code,'code_verifier'=>$pending['verifier']]);
        $token=$response['access_token']??null;
        if(!is_string($token)||!preg_match('/^[A-Za-z0-9_]+$/D',$token)||strlen($token)>512){throw new InvalidArgumentException('GitHub no autorizó el ingreso.');}
        $headers=['Accept: application/vnd.github+json','X-GitHub-Api-Version: 2022-11-28','Authorization: Bearer '.$token];
        $profile=$fetch('https://api.github.com/user',$headers,null);
        $emails=$fetch('https://api.github.com/user/emails?per_page=100',$headers,null);
        $githubId=(string)($profile['id']??'');
        if(!preg_match('/^[0-9]{1,20}$/D',$githubId)||$githubId==='0'){throw new InvalidArgumentException('No se pudo verificar la identidad de GitHub.');}
        $primary=[];foreach($emails as $email){if(is_array($email)&&($email['primary']??false)===true&&($email['verified']??false)===true&&is_string($email['email']??null)&&filter_var($email['email'],FILTER_VALIDATE_EMAIL)){$primary[]=strtolower(trim($email['email']));}}
        if(count($primary)!==1){throw new InvalidArgumentException('Tu cuenta GitHub necesita un email principal verificado.');}
        db()->beginTransaction();
        try{
            $user=query("SELECT * FROM usuarios WHERE LOWER(TRIM(correo))=? AND tipo_usuario='ALUMNO' AND activo=1 FOR UPDATE",[$primary[0]])->fetch();
            if(!$user||($user['github_id']!==null&&(string)$user['github_id']!==$githubId)){throw new InvalidArgumentException('El email principal verificado de GitHub debe coincidir con una cuenta de estudiante activa registrada en SGLAB.');}
            $other=query('SELECT ci FROM usuarios WHERE github_id=? AND ci<>?',[$githubId,$user['ci']])->fetch();
            if($other){throw new InvalidArgumentException('Esta cuenta GitHub ya está vinculada a otra persona. Consultá al administrador.');}
            query('UPDATE usuarios SET github_id=? WHERE ci=?',[$githubId,$user['ci']]);$user['github_id']=$githubId;
            db()->commit();
        }catch(Throwable $exc){if(db()->inTransaction()){db()->rollBack();}throw $exc;}
        Auth::complete($user,'github');
    }
}
