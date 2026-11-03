<?php
declare(strict_types=1);
require __DIR__ . '/../src/bootstrap.php';
ob_start();
header('Content-Type: text/html; charset=utf-8');
header('Cache-Control: no-store');
header('X-Content-Type-Options: nosniff');
header('Referrer-Policy: no-referrer');
header("Content-Security-Policy: default-src 'self'; style-src 'self'; img-src 'self' data:; script-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'");
$page = is_string($_GET['page'] ?? null) ? $_GET['page'] : 'inicio';
$error='';
try {
    Auth::start();
    if($page==='github_callback'&&$_SERVER['REQUEST_METHOD']==='GET'){GithubAuth::callback($_GET);redirect('inicio');}
    if($page==='mfa_qr'&&$_SERVER['REQUEST_METHOD']==='GET'){header('Content-Type: image/svg+xml; charset=utf-8');echo Mfa::qr();exit;}
    if ($_SERVER['REQUEST_METHOD']==='POST') {
        if (!hash_equals($_SESSION['csrf'], input('csrf'))) { http_response_code(403); throw new RuntimeException('El formulario venció. Recargá la página y volvé a intentar.'); }
        $action=input('action');
        if ($action==='login') {
            Auth::login(input('ci'), is_string($_POST['password']??null) ? $_POST['password'] : ''); redirect(Mfa::pending()?'mfa':'inicio');
        }
        if($action==='github_start'){header('Location: '.GithubAuth::begin(),true,303);exit;}
        if($action==='mfa_verify'){Mfa::confirm(input('code'));redirect('inicio');}
        if($action==='cancel_login'){Auth::logout();redirect('login');}
        if (!isset($_SESSION['user'])) { redirect('login'); }
        if ($action==='logout') { Auth::logout(); redirect('login'); }
        if ($action==='save_lab') { Inventory::saveLab(); }
        if ($action==='import_equipment') { EquipmentCsv::import(); }
        if ($action==='save_equipment') { Inventory::saveEquipment(); }
        if ($action==='archive_lab') { Inventory::archive('lab'); }
        if ($action==='archive_equipment') { Inventory::archive('equipment'); }
        if ($action==='report_function') { Reports::save(); }
        if ($action==='save_comment') { Comments::save(); }
        if ($action==='import_users') { PeopleCsv::import(); }
        if ($action==='save_user') { People::save(); }
        if ($action==='assign_user') { People::assign(); }
        if ($action==='revoke_assignment') { People::assign(true); }
        throw new InvalidArgumentException('Acción desconocida.');
    }
} catch (HttpError $exc) { http_response_code($exc->status); $error=$exc->getMessage(); $page='error'; }
catch (InvalidArgumentException $exc) { $error=$exc->getMessage(); }
catch (PDOException $exc) {
    error_log('SGLAB DB: '.$exc->getCode());
    $error=$exc->getCode()==='23000' ? 'Los datos coinciden con un registro existente. Revisá la serie y el UUID.' : 'No se pudo completar la operación. Intentá nuevamente.';
    http_response_code(503);
} catch (RuntimeException $exc) { $error=$exc->getMessage(); }
catch (Throwable $exc) { error_log('SGLAB: '.get_class($exc)); http_response_code(503); $error='El servicio no está disponible. Intentá más tarde.'; }
if (!isset($_SESSION['user'])) { view(Mfa::pending()?'mfa':'login',['error'=>$error]); exit; }
if ($page==='login') { redirect('inicio'); }
if (!in_array($page,['inicio','laboratorios','laboratorio','equipos','equipo','usuarios','historial','error'],true)) { http_response_code(404); $page='missing'; }
try {
    Access::requirePage($page);
    if($page==='historial'){
        History::authorize();
        $historyFilters=History::filters($_GET);
        if(isset($_GET['exportar'])){
            if($_GET['exportar']!=='csv'){throw new InvalidArgumentException('Formato de exportación inválido.');}
            History::export($historyFilters);
        }
    }
    view('layout',['page'=>$page,'error'=>$error]);
}
catch (HttpError $exc) { ob_clean(); http_response_code($exc->status); view('layout',['page'=>'error','error'=>$exc->getMessage()]); }
catch (InvalidArgumentException $exc) { ob_clean(); http_response_code(400); view('layout',['page'=>'error','error'=>$exc->getMessage()]); }
catch (Throwable $exc) { ob_clean(); error_log('SGLAB render: '.get_class($exc)); http_response_code(503); view('layout',['page'=>'error','error'=>'No se pudo cargar la página. Intentá nuevamente.']); }
